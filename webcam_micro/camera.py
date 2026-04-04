"""Camera discovery, preview, and control backends for the prototype."""

from __future__ import annotations

import contextlib
import glob
import math
import re
import shutil
import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class CameraDescriptor:
    """Describe one backend-exposed camera candidate."""

    stable_id: str
    display_name: str
    backend_name: str
    device_selector: str
    native_identifier: str | None = None
    display_occurrence_index: int = 0


@dataclass(frozen=True)
class CameraControlChoice:
    """Describe one selectable option for an enumerated control."""

    value: str
    label: str


@dataclass(frozen=True)
class CameraControl:
    """Describe one user-facing camera control."""

    control_id: str
    label: str
    kind: str
    value: object | None
    choices: tuple[CameraControlChoice, ...] = ()
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    read_only: bool = False
    enabled: bool = True
    unit: str = ""
    details: str = ""
    action_label: str = ""


class CameraControlError(RuntimeError):
    """Raised when camera controls are unavailable or fail to apply."""


class CameraControlApplyError(CameraControlError):
    """Raised when one control value cannot be applied."""


class CameraOutputError(RuntimeError):
    """Raised when still or recording output work cannot complete."""


class CameraSession(Protocol):
    """Represent one open camera session lifecycle."""

    def close(self) -> None:
        """Release backend resources for the active session."""

    def get_latest_frame(self) -> PreviewFrame | None:
        """Return the newest available preview frame."""

    @property
    def failure_reason(self) -> str | None:
        """Return the most recent recoverable session failure."""

    def start_recording(self, output_path: Path) -> Path:
        """Start recording to one output path."""

    def stop_recording(self) -> Path | None:
        """Stop the active recording and return the resolved output path."""

    @property
    def recording_available(self) -> bool:
        """Return whether the session can start a recording."""

    @property
    def recording_state(self) -> str:
        """Return the current recording state label."""

    @property
    def recording_duration_milliseconds(self) -> int:
        """Return the current recording duration in milliseconds."""

    @property
    def recording_output_path(self) -> Path | None:
        """Return the active or last recording output path."""

    @property
    def recording_error(self) -> str | None:
        """Return the most recent recoverable recording failure."""


class CameraBackend(Protocol):
    """Represent the shared camera-backend contract used by the UI."""

    backend_name: str

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return the cameras the backend can currently expose."""

    def open_session(self, descriptor: CameraDescriptor) -> CameraSession:
        """Open one camera session for the provided descriptor."""

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the current control surface for the selected camera."""

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one control value for the selected camera."""

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one action-style control for the selected camera."""


class CameraControlBackend(Protocol):
    """Represent the control-management surface behind one backend."""

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the current control surface for one descriptor."""

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one camera-control value."""

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one action-style control."""


@dataclass(frozen=True)
class PreviewFrame:
    """Represent one RGB preview frame for the UI."""

    width: int
    height: int
    rgb_bytes: bytes
    frame_number: int


@dataclass(frozen=True)
class BackendPlan:
    """Summarize the chosen backend direction for the prototype."""

    active_backend: str
    first_device_backend_target: str
    notes: tuple[str, ...]


def build_backend_plan() -> BackendPlan:
    """Return the documented backend baseline for the prototype."""

    return BackendPlan(
        active_backend="QtCameraBackend",
        first_device_backend_target=(
            "Qt Multimedia-backed discovery and live preview"
        ),
        notes=(
            "Stage 7 moves camera discovery and live preview onto Qt "
            "Multimedia camera devices and capture sessions.",
            "Preview readers keep only the newest frame surfaced through a "
            "QVideoSink so the workspace renderer does not lag behind live "
            "video.",
            "The typed control surface still uses AVFoundation for macOS "
            "camera-control access when available.",
        ),
    )


@dataclass
class NullCameraSession:
    """Represent one placeholder camera session for the null backend."""

    descriptor: CameraDescriptor
    closed: bool = False

    def close(self) -> None:
        """Mark the placeholder session as closed."""

        self.closed = True

    def get_latest_frame(self) -> PreviewFrame | None:
        """Return no frame for the placeholder backend."""

        return None

    @property
    def failure_reason(self) -> str | None:
        """Return no runtime failure for the placeholder backend."""

        return None

    def start_recording(self, output_path: Path) -> Path:
        """Raise because the placeholder session cannot record."""

        raise CameraOutputError(
            "Recording is unavailable for the placeholder camera backend."
        )

    def stop_recording(self) -> Path | None:
        """Return no path because the placeholder session never records."""

        return None

    @property
    def recording_available(self) -> bool:
        """Return that the placeholder backend cannot record."""

        return False

    @property
    def recording_state(self) -> str:
        """Return the placeholder recording state."""

        return "not ready"

    @property
    def recording_duration_milliseconds(self) -> int:
        """Return zero because the placeholder backend never records."""

        return 0

    @property
    def recording_output_path(self) -> Path | None:
        """Return no path because no recording exists."""

        return None

    @property
    def recording_error(self) -> str | None:
        """Return no recording error for the placeholder backend."""

        return None


class NullCameraControlBackend:
    """Provide an empty control surface when no real controls exist."""

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return no controls for the placeholder backend."""

        return ()

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Raise because the null backend has no writable controls."""

        raise CameraControlApplyError(
            "No writable controls are available for this camera backend."
        )

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Raise because the null backend has no action controls."""

        raise CameraControlApplyError(
            "No action controls are available for this camera backend."
        )


class NullCameraBackend:
    """Provide a fallback backend when real device I/O is unavailable."""

    backend_name = "null"

    def __init__(self) -> None:
        """Initialize the placeholder backend and its empty controls."""

        self._control_backend = NullCameraControlBackend()

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return no devices for the placeholder backend."""

        return ()

    def open_session(self, descriptor: CameraDescriptor) -> NullCameraSession:
        """Return a placeholder session for the requested descriptor."""

        return NullCameraSession(descriptor=descriptor)

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return no controls for the placeholder backend."""

        return self._control_backend.list_controls(descriptor)

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Forward a control write to the empty control backend."""

        self._control_backend.set_control_value(descriptor, control_id, value)

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Forward an action request to the empty control backend."""

        self._control_backend.trigger_control_action(descriptor, control_id)


class MissingCameraDependencyError(RuntimeError):
    """Raised when the runtime camera backend dependency is unavailable."""


def _load_qt_camera_modules():
    """Import Qt Multimedia lazily so smoke tests stay lightweight."""

    try:
        from PySide6 import QtCore, QtGui, QtMultimedia
    except ModuleNotFoundError:
        return None, None, None
    return QtCore, QtGui, QtMultimedia


def _load_avfoundation_modules():
    """Import the macOS control bridge lazily when it is available."""

    if sys.platform != "darwin":
        return None, None
    try:
        from rubicon.objc import ObjCClass, objc_const
        from rubicon.objc.runtime import load_library
    except ModuleNotFoundError:
        return None, None
    framework = load_library("AVFoundation")
    capture_device_class = ObjCClass("AVCaptureDevice")
    media_type_video = objc_const(framework, "AVMediaTypeVideo")
    return capture_device_class, media_type_video


def _call_or_value(value: object) -> object:
    """Return the result of a bound Objective-C method or the raw value."""

    if callable(value):
        return value()
    return value


def _ffmpeg_executable() -> str:
    """Return a fallback FFmpeg binary path from the current machine."""

    ffmpeg_executable = shutil.which("ffmpeg")
    if ffmpeg_executable is None:
        raise MissingCameraDependencyError(
            "Install ffmpeg and make sure it is on PATH before opening the "
            "fallback FFmpeg backend."
        )
    return ffmpeg_executable


def _qt_camera_identifier_text(identifier: bytes) -> str | None:
    """Return a stable text identifier for one Qt camera-device id."""

    if not identifier:
        return None
    try:
        decoded = identifier.decode("utf-8").strip("\x00")
    except UnicodeDecodeError:
        decoded = ""
    if decoded:
        return decoded
    return identifier.hex()


def _qt_camera_stable_id(device: object, *, fallback_index: int) -> str:
    """Return one stable descriptor id for a Qt camera device."""

    raw_identifier = bytes(device.id())
    identifier = _qt_camera_identifier_text(raw_identifier)
    if identifier:
        return f"qt-camera::{identifier}"
    return f"qt-camera::{fallback_index}"


def _qt_camera_label(
    *,
    display_name: str,
    identifier: str | None,
    default_identifier: str | None,
) -> str:
    """Return the user-visible label for one Qt camera device."""

    if identifier is not None and identifier == default_identifier:
        return f"{display_name} (Default)"
    return display_name


def _discover_qt_cameras() -> tuple[CameraDescriptor, ...]:
    """Discover cameras through Qt Multimedia video-input devices."""

    _qt_core, _qt_gui, qt_multimedia = _load_qt_camera_modules()
    if qt_multimedia is None:
        raise MissingCameraDependencyError(
            "Install the package runtime dependencies before opening a "
            "camera session."
        )
    default_device = qt_multimedia.QMediaDevices.defaultVideoInput()
    default_identifier = _qt_camera_identifier_text(bytes(default_device.id()))
    counts: dict[str, int] = {}
    descriptors: list[CameraDescriptor] = []
    for index, device in enumerate(qt_multimedia.QMediaDevices.videoInputs()):
        display_name = device.description() or f"Camera {index + 1}"
        occurrence_index = counts.get(display_name, 0)
        counts[display_name] = occurrence_index + 1
        identifier = _qt_camera_identifier_text(bytes(device.id()))
        stable_id = _qt_camera_stable_id(device, fallback_index=index)
        descriptors.append(
            CameraDescriptor(
                stable_id=stable_id,
                display_name=_qt_camera_label(
                    display_name=display_name,
                    identifier=identifier,
                    default_identifier=default_identifier,
                ),
                backend_name="qt_multimedia",
                device_selector=stable_id,
                native_identifier=identifier,
                display_occurrence_index=occurrence_index,
            )
        )
    return tuple(descriptors)


def pack_preview_rgb_rows(
    raw_bytes: bytes | bytearray | memoryview,
    *,
    width: int,
    height: int,
    bytes_per_line: int,
) -> bytes:
    """Pack padded RGB rows into one tightly packed preview payload."""

    row_width = width * 3
    trimmed = bytes(raw_bytes)[: bytes_per_line * height]
    if bytes_per_line == row_width:
        return trimmed[: row_width * height]
    return b"".join(
        trimmed[
            row_index * bytes_per_line : row_index * bytes_per_line + row_width
        ]
        for row_index in range(height)
    )


def _rotation_angle_degrees(rotation_angle: object) -> int:
    """Return the numeric degrees stored in one Qt rotation enum/value."""

    raw_value = getattr(rotation_angle, "value", rotation_angle)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return 0


def _qimage_to_preview_frame(
    image: Any,
    *,
    qt_gui: Any,
    frame_number: int,
) -> PreviewFrame:
    """Convert one Qt image into the shared packed RGB preview payload."""

    rgb_image = image.convertToFormat(qt_gui.QImage.Format.Format_RGB888)
    width = int(rgb_image.width())
    height = int(rgb_image.height())
    return PreviewFrame(
        width=width,
        height=height,
        rgb_bytes=pack_preview_rgb_rows(
            rgb_image.bits(),
            width=width,
            height=height,
            bytes_per_line=int(rgb_image.bytesPerLine()),
        ),
        frame_number=frame_number,
    )


def _qt_media_file_format_for_path(path: Path, qt_multimedia: Any) -> object:
    """Return one Qt media file format that matches the output suffix."""

    suffix = path.suffix.lower()
    formats = qt_multimedia.QMediaFormat.FileFormat
    if suffix == ".mov":
        return formats.QuickTime
    if suffix == ".mkv":
        return formats.Matroska
    if suffix == ".webm":
        return formats.WebM
    return formats.MPEG4


def _qt_recorder_state_text(state: object, qt_multimedia: Any) -> str:
    """Return a readable recording-state label for one Qt enum value."""

    states = qt_multimedia.QMediaRecorder.RecorderState
    if state == states.RecordingState:
        return "recording"
    if state == states.PausedState:
        return "paused"
    return "stopped"


def _run_discovery_command(command: list[str]) -> str:
    """Run a discovery command and combine stdout plus stderr text."""

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return "\n".join(
        chunk for chunk in (completed.stdout, completed.stderr) if chunk
    )


@dataclass(frozen=True)
class _MacosVideoDevice:
    """Describe one AVFoundation video device for discovery matching."""

    display_name: str
    unique_id: str
    occurrence_index: int


def _macos_video_devices() -> tuple[_MacosVideoDevice, ...]:
    """Return AVFoundation devices for matching FFmpeg descriptors."""

    capture_device_class, media_type_video = _load_avfoundation_modules()
    if capture_device_class is None or media_type_video is None:
        return ()
    try:
        devices = capture_device_class.devicesWithMediaType_(media_type_video)
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        return ()
    counts: dict[str, int] = {}
    descriptors: list[_MacosVideoDevice] = []
    for device in devices:
        display_name = str(_call_or_value(device.localizedName))
        occurrence_index = counts.get(display_name, 0)
        counts[display_name] = occurrence_index + 1
        descriptors.append(
            _MacosVideoDevice(
                display_name=display_name,
                unique_id=str(_call_or_value(device.uniqueID)),
                occurrence_index=occurrence_index,
            )
        )
    return tuple(descriptors)


def _match_macos_video_device(
    display_name: str,
    occurrence_index: int,
    devices: tuple[_MacosVideoDevice, ...],
) -> _MacosVideoDevice | None:
    """Return the AVFoundation device matching one FFmpeg display slot."""

    for descriptor in devices:
        if (
            descriptor.display_name == display_name
            and descriptor.occurrence_index == occurrence_index
        ):
            return descriptor
    return None


def _discover_macos_cameras(ffmpeg_exe: str) -> tuple[CameraDescriptor, ...]:
    """Discover cameras through FFmpeg's AVFoundation device listing."""

    output = _run_discovery_command(
        [
            ffmpeg_exe,
            "-hide_banner",
            "-f",
            "avfoundation",
            "-list_devices",
            "true",
            "-i",
            "",
        ]
    )
    avfoundation_devices = _macos_video_devices()
    name_occurrence_counts: dict[str, int] = {}
    descriptors: list[CameraDescriptor] = []
    in_video_section = False
    pattern = re.compile(r"\[(?P<index>\d+)\]\s+(?P<name>.+)$")
    for line in output.splitlines():
        if "AVFoundation video devices" in line:
            in_video_section = True
            continue
        if "AVFoundation audio devices" in line:
            break
        if not in_video_section:
            continue
        match = pattern.search(line)
        if match is None:
            continue
        device_index = match.group("index")
        device_name = match.group("name").strip()
        occurrence_index = name_occurrence_counts.get(device_name, 0)
        name_occurrence_counts[device_name] = occurrence_index + 1
        matched_device = _match_macos_video_device(
            device_name,
            occurrence_index,
            avfoundation_devices,
        )
        descriptors.append(
            CameraDescriptor(
                stable_id=f"ffmpeg:avfoundation:{device_index}",
                display_name=device_name,
                backend_name="ffmpeg",
                device_selector=device_index,
                native_identifier=(
                    matched_device.unique_id if matched_device else None
                ),
                display_occurrence_index=occurrence_index,
            )
        )
    return tuple(descriptors)


def _linux_device_label(device_path: str) -> str:
    """Return the most useful Linux label we can derive for one device."""

    device_name = Path(device_path).name
    sysfs_name = Path("/sys/class/video4linux") / device_name / "name"
    if sysfs_name.exists():
        label = sysfs_name.read_text(encoding="utf-8").strip()
        if label:
            return f"{label} ({device_path})"
    return device_path


def _discover_linux_cameras() -> tuple[CameraDescriptor, ...]:
    """Discover Linux cameras from the standard V4L2 device nodes."""

    descriptors: list[CameraDescriptor] = []
    for device_path in sorted(glob.glob("/dev/video*")):
        device_name = Path(device_path).name
        descriptors.append(
            CameraDescriptor(
                stable_id=f"ffmpeg:v4l2:{device_name}",
                display_name=_linux_device_label(device_path),
                backend_name="ffmpeg",
                device_selector=device_path,
            )
        )
    return tuple(descriptors)


def _discover_windows_cameras(
    ffmpeg_exe: str,
) -> tuple[CameraDescriptor, ...]:
    """Discover cameras through FFmpeg's DirectShow device listing."""

    output = _run_discovery_command(
        [
            ffmpeg_exe,
            "-hide_banner",
            "-list_devices",
            "true",
            "-f",
            "dshow",
            "-i",
            "dummy",
        ]
    )
    descriptors: list[CameraDescriptor] = []
    in_video_section = False
    for line in output.splitlines():
        if "DirectShow video devices" in line:
            in_video_section = True
            continue
        if "DirectShow audio devices" in line:
            break
        if not in_video_section or '"' not in line:
            continue
        start = line.find('"')
        end = line.rfind('"')
        if start == -1 or end <= start:
            continue
        device_name = line[start + 1 : end].strip()
        if not device_name or device_name.startswith("@device"):
            continue
        stable_slug = re.sub(r"[^a-z0-9]+", "-", device_name.lower()).strip(
            "-"
        )
        descriptors.append(
            CameraDescriptor(
                stable_id=f"ffmpeg:dshow:{stable_slug or 'camera'}",
                display_name=device_name,
                backend_name="ffmpeg",
                device_selector=device_name,
            )
        )
    return tuple(descriptors)


def _discover_ffmpeg_cameras(
    ffmpeg_exe: str,
) -> tuple[CameraDescriptor, ...]:
    """Return the discovered cameras for the current platform."""

    if sys.platform == "darwin":
        return _discover_macos_cameras(ffmpeg_exe)
    if sys.platform.startswith("win"):
        return _discover_windows_cameras(ffmpeg_exe)
    return _discover_linux_cameras()


def _input_args(device_selector: str) -> tuple[str, ...]:
    """Return the FFmpeg input arguments for the current platform."""

    if sys.platform == "darwin":
        return (
            "-f",
            "avfoundation",
            "-framerate",
            "30",
            "-i",
            f"{device_selector}:none",
        )
    if sys.platform.startswith("win"):
        return (
            "-f",
            "dshow",
            "-framerate",
            "30",
            "-i",
            f"video={device_selector}",
        )
    return (
        "-f",
        "v4l2",
        "-framerate",
        "30",
        "-i",
        device_selector,
    )


def _safe_float(value: object) -> float | None:
    """Return a finite float for the provided value when possible."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _numeric_step(
    minimum: float,
    maximum: float,
    *,
    preferred_steps: int = 100,
) -> float:
    """Return a small but usable step size for numeric controls."""

    span = maximum - minimum
    if span <= 0:
        return 0.1
    return max(span / preferred_steps, 0.01)


def _choice_for_value(
    choices: tuple[CameraControlChoice, ...],
    value: str,
) -> CameraControlChoice | None:
    """Return the first choice matching the provided control value."""

    for choice in choices:
        if choice.value == value:
            return choice
    return None


class AvFoundationCameraControlBackend:
    """Expose macOS AVFoundation camera controls when the bridge is present."""

    def __init__(self) -> None:
        """Load the bridge modules used to inspect and configure controls."""

        self._capture_device_class, self._video_media_type = (
            _load_avfoundation_modules()
        )

    @property
    def available(self) -> bool:
        """Return whether the macOS control bridge is ready."""

        return (
            self._capture_device_class is not None
            and self._video_media_type is not None
        )

    def _device_for_descriptor(
        self, descriptor: CameraDescriptor
    ) -> Any | None:
        """Return the AVFoundation device matching the provided descriptor."""

        if not self.available:
            return None
        assert self._capture_device_class is not None
        assert self._video_media_type is not None
        devices = self._capture_device_class.devicesWithMediaType_(
            self._video_media_type
        )
        if descriptor.native_identifier is not None:
            for device in devices:
                if (
                    str(_call_or_value(device.uniqueID))
                    == descriptor.native_identifier
                ):
                    return device
        matching_name_devices = [
            device
            for device in devices
            if str(_call_or_value(device.localizedName))
            == descriptor.display_name
        ]
        if descriptor.display_occurrence_index < len(matching_name_devices):
            return matching_name_devices[descriptor.display_occurrence_index]
        return None

    def _exposure_mode_choices(
        self, device: Any
    ) -> tuple[CameraControlChoice, ...]:
        """Return the writable exposure-mode choices for one device."""

        choices: list[CameraControlChoice] = []
        supported_modes = (
            (0, "locked", "Locked"),
            (2, "continuous_auto", "Continuous Auto"),
        )
        for mode_value, value_name, label in supported_modes:
            if device.isExposureModeSupported_(mode_value):
                choices.append(
                    CameraControlChoice(value=value_name, label=label)
                )
        return tuple(choices)

    def _exposure_mode_name(self, device: Any) -> str:
        """Return the current exposure mode as a stable string token."""

        mode_map = {
            0: "locked",
            2: "continuous_auto",
        }
        return mode_map.get(int(_call_or_value(device.exposureMode)), "locked")

    def _source_mode_text(self, device: Any) -> str:
        """Return a readable active-format summary for one device."""

        active_format = _call_or_value(device.activeFormat)
        return str(active_format)

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the current AVFoundation control surface."""

        if not self.available:
            return ()
        device = self._device_for_descriptor(descriptor)
        if device is None:
            return ()
        controls: list[CameraControl] = []

        exposure_choices = self._exposure_mode_choices(device)
        if exposure_choices:
            current_exposure_mode = self._exposure_mode_name(device)
            controls.append(
                CameraControl(
                    control_id="exposure_mode",
                    label="Exposure Mode",
                    kind="enum",
                    value=current_exposure_mode,
                    choices=exposure_choices,
                    details=(
                        "AVFoundation exposure mode for the active camera."
                    ),
                )
            )
            supports_lock_toggle = (
                _choice_for_value(exposure_choices, "locked") is not None
                and _choice_for_value(exposure_choices, "continuous_auto")
                is not None
            )
            if supports_lock_toggle:
                controls.append(
                    CameraControl(
                        control_id="exposure_locked",
                        label="Exposure Locked",
                        kind="boolean",
                        value=current_exposure_mode == "locked",
                        details=(
                            "Convenience toggle between locked and "
                            "continuous auto exposure."
                        ),
                    )
                )

        zoom_minimum = (
            _safe_float(_call_or_value(device.minAvailableVideoZoomFactor))
            or 1.0
        )
        zoom_maximum = (
            _safe_float(_call_or_value(device.maxAvailableVideoZoomFactor))
            or 1.0
        )
        zoom_value = (
            _safe_float(_call_or_value(device.videoZoomFactor)) or zoom_minimum
        )
        zoom_writable = zoom_maximum > zoom_minimum + 0.001
        controls.append(
            CameraControl(
                control_id="zoom_factor",
                label="Zoom Factor",
                kind="numeric",
                value=zoom_value,
                min_value=zoom_minimum,
                max_value=zoom_maximum,
                step=_numeric_step(zoom_minimum, zoom_maximum),
                read_only=not zoom_writable,
                enabled=zoom_writable,
                unit="x",
                details="AVFoundation video zoom factor.",
            )
        )

        controls.append(
            CameraControl(
                control_id="active_format",
                label="Active Format",
                kind="read_only",
                value=self._source_mode_text(device),
                details="Current AVFoundation source mode.",
            )
        )
        controls.append(
            CameraControl(
                control_id="control_backend",
                label="Control Backend",
                kind="read_only",
                value="AVFoundation",
                details="Native control bridge used for macOS cameras.",
            )
        )
        controls.append(
            CameraControl(
                control_id="low_light_boost_support",
                label="Low Light Boost Supported",
                kind="read_only",
                value="Yes" if device.isLowLightBoostSupported() else "No",
                details=(
                    "Reports whether AVFoundation exposes low-light boost."
                ),
            )
        )

        if _choice_for_value(exposure_choices, "continuous_auto") is not None:
            controls.append(
                CameraControl(
                    control_id="restore_auto_exposure",
                    label="Restore Auto Exposure",
                    kind="action",
                    value=None,
                    action_label="Restore",
                    details=("Return the device to continuous auto exposure."),
                )
            )

        return tuple(controls)

    def _lock_device(self, device: Any) -> None:
        """Lock one device for configuration or raise a readable error."""

        lock_result = device.lockForConfiguration_(None)
        if isinstance(lock_result, tuple):
            locked, error = lock_result
        else:
            locked, error = bool(lock_result), None
        if not locked:
            message = str(error) if error else "Could not lock camera."
            raise CameraControlApplyError(message)

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one AVFoundation control value."""

        if not self.available:
            raise CameraControlApplyError(
                "The macOS camera-control bridge is not installed."
            )
        device = self._device_for_descriptor(descriptor)
        if device is None:
            raise CameraControlApplyError(
                "The selected camera could not be found for control updates."
            )
        self._lock_device(device)
        try:
            if control_id == "exposure_mode":
                mode_map = {
                    "locked": 0,
                    "continuous_auto": 2,
                }
                mode_value = mode_map.get(str(value))
                if mode_value is None:
                    raise CameraControlApplyError(
                        "Unsupported exposure mode selection."
                    )
                if not device.isExposureModeSupported_(mode_value):
                    raise CameraControlApplyError(
                        "The camera does not support that exposure mode."
                    )
                device.setExposureMode_(mode_value)
                return
            if control_id == "exposure_locked":
                mode_value = 0 if bool(value) else 2
                if not device.isExposureModeSupported_(mode_value):
                    raise CameraControlApplyError(
                        "The camera cannot switch exposure lock state."
                    )
                device.setExposureMode_(mode_value)
                return
            if control_id == "zoom_factor":
                zoom_value = _safe_float(value)
                if zoom_value is None:
                    raise CameraControlApplyError("Zoom must be numeric.")
                minimum = (
                    _safe_float(
                        _call_or_value(device.minAvailableVideoZoomFactor)
                    )
                    or 1.0
                )
                maximum = (
                    _safe_float(
                        _call_or_value(device.maxAvailableVideoZoomFactor)
                    )
                    or 1.0
                )
                if maximum <= minimum + 0.001:
                    raise CameraControlApplyError(
                        "Zoom is fixed on this camera."
                    )
                bounded_value = max(minimum, min(maximum, zoom_value))
                device.setVideoZoomFactor_(bounded_value)
                return
            raise CameraControlApplyError(
                f"Unsupported camera control `{control_id}`."
            )
        finally:
            device.unlockForConfiguration()

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one AVFoundation action control."""

        if control_id != "restore_auto_exposure":
            raise CameraControlApplyError(
                f"Unsupported action control `{control_id}`."
            )
        self.set_control_value(
            descriptor,
            "exposure_mode",
            "continuous_auto",
        )


class QtCameraSession:
    """Capture preview frames from one Qt Multimedia camera session."""

    def __init__(
        self,
        descriptor: CameraDescriptor,
        camera_device: Any,
        *,
        qt_core: Any,
        qt_gui: Any,
        qt_multimedia: Any,
    ) -> None:
        """Start one Qt camera, capture session, and preview sink."""

        self.descriptor = descriptor
        self._qt_core = qt_core
        self._qt_gui = qt_gui
        self._qt_multimedia = qt_multimedia
        self._camera = qt_multimedia.QCamera(camera_device)
        self._capture_session = qt_multimedia.QMediaCaptureSession()
        self._video_sink = qt_multimedia.QVideoSink()
        self._media_recorder = qt_multimedia.QMediaRecorder()
        self._capture_session.setCamera(self._camera)
        self._capture_session.setVideoSink(self._video_sink)
        self._capture_session.setRecorder(self._media_recorder)
        self._latest_frame: PreviewFrame | None = None
        self._failure_reason: str | None = None
        self._recording_error: str | None = None
        self._recording_state = "stopped"
        self._recording_duration_milliseconds = 0
        self._recording_output_path: Path | None = None
        self._frame_number = -1
        self._closed = False

        self._video_sink.videoFrameChanged.connect(self._handle_video_frame)
        self._camera.errorOccurred.connect(self._handle_camera_error)
        self._media_recorder.recorderStateChanged.connect(
            self._handle_recorder_state_changed
        )
        self._media_recorder.durationChanged.connect(
            self._handle_duration_changed
        )
        self._media_recorder.actualLocationChanged.connect(
            self._handle_actual_location_changed
        )
        self._media_recorder.errorOccurred.connect(self._handle_recorder_error)
        self._camera.start()

    def _handle_camera_error(self, _error: object, message: str) -> None:
        """Record the most recent camera error message for the session."""

        if message:
            self._failure_reason = message
            return
        self._failure_reason = "Qt Multimedia preview failed."

    def _handle_video_frame(self, frame: Any) -> None:
        """Convert the newest Qt video frame into one packed RGB preview."""

        if self._closed or not frame.isValid():
            return
        image = frame.toImage()
        if image.isNull():
            return
        if frame.mirrored():
            image = image.mirrored(True, False)
        rotation_degrees = _rotation_angle_degrees(frame.rotationAngle())
        if rotation_degrees:
            transform = self._qt_gui.QTransform()
            transform.rotate(rotation_degrees)
            image = image.transformed(transform)
        self._frame_number += 1
        self._latest_frame = _qimage_to_preview_frame(
            image,
            qt_gui=self._qt_gui,
            frame_number=self._frame_number,
        )
        self._failure_reason = None

    def _handle_recorder_state_changed(self, state: object) -> None:
        """Mirror the Qt recorder state into a stable string label."""

        self._recording_state = _qt_recorder_state_text(
            state,
            self._qt_multimedia,
        )

    def _handle_duration_changed(self, duration: int) -> None:
        """Store the current recording duration in milliseconds."""

        self._recording_duration_milliseconds = max(0, int(duration))

    def _handle_actual_location_changed(self, location: object) -> None:
        """Store the resolved recording output location when Qt reports it."""

        if location is None:
            return
        local_path = location.toLocalFile()
        if local_path:
            self._recording_output_path = Path(local_path)

    def _handle_recorder_error(self, _error: object, message: str) -> None:
        """Record the newest visible recording error message."""

        if message:
            self._recording_error = message
            return
        self._recording_error = "Qt Multimedia recording failed."

    def start_recording(self, output_path: Path) -> Path:
        """Start one Qt Multimedia recording to the requested path."""

        if self._closed:
            raise CameraOutputError("The active camera session is closed.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        media_format = self._qt_multimedia.QMediaFormat()
        media_format.setFileFormat(
            _qt_media_file_format_for_path(
                output_path,
                self._qt_multimedia,
            )
        )
        self._media_recorder.setMediaFormat(media_format)
        self._media_recorder.setQuality(
            self._qt_multimedia.QMediaRecorder.Quality.HighQuality
        )
        self._media_recorder.setOutputLocation(
            self._qt_core.QUrl.fromLocalFile(str(output_path))
        )
        self._recording_error = None
        self._recording_duration_milliseconds = 0
        self._recording_output_path = output_path
        self._media_recorder.record()
        return output_path

    def stop_recording(self) -> Path | None:
        """Stop the active Qt Multimedia recording cleanly."""

        if self._recording_state != "recording":
            return self._recording_output_path
        self._media_recorder.stop()
        return self._recording_output_path

    def close(self) -> None:
        """Stop the Qt camera and disconnect the preview sink cleanly."""

        if self._closed:
            return
        self._closed = True
        with contextlib.suppress(Exception):
            self._video_sink.videoFrameChanged.disconnect(
                self._handle_video_frame
            )
        with contextlib.suppress(Exception):
            self._camera.errorOccurred.disconnect(self._handle_camera_error)
        with contextlib.suppress(Exception):
            self._media_recorder.recorderStateChanged.disconnect(
                self._handle_recorder_state_changed
            )
        with contextlib.suppress(Exception):
            self._media_recorder.durationChanged.disconnect(
                self._handle_duration_changed
            )
        with contextlib.suppress(Exception):
            self._media_recorder.actualLocationChanged.disconnect(
                self._handle_actual_location_changed
            )
        with contextlib.suppress(Exception):
            self._media_recorder.errorOccurred.disconnect(
                self._handle_recorder_error
            )
        with contextlib.suppress(Exception):
            self._media_recorder.stop()
        with contextlib.suppress(Exception):
            self._camera.stop()

    def get_latest_frame(self) -> PreviewFrame | None:
        """Return the newest available Qt preview frame."""

        return self._latest_frame

    @property
    def failure_reason(self) -> str | None:
        """Return the most recent recoverable Qt session failure."""

        return self._failure_reason

    @property
    def recording_available(self) -> bool:
        """Return whether this Qt session can start a recording."""

        return not self._closed

    @property
    def recording_state(self) -> str:
        """Return the current recorder-state label."""

        return self._recording_state

    @property
    def recording_duration_milliseconds(self) -> int:
        """Return the current recorder duration in milliseconds."""

        return self._recording_duration_milliseconds

    @property
    def recording_output_path(self) -> Path | None:
        """Return the current or last recording output path."""

        return self._recording_output_path

    @property
    def recording_error(self) -> str | None:
        """Return the newest recoverable recording error."""

        return self._recording_error


class FfmpegCameraSession:
    """Capture preview frames from one FFmpeg camera session."""

    def __init__(
        self,
        descriptor: CameraDescriptor,
        process: subprocess.Popen[bytes],
        *,
        width: int,
        height: int,
    ) -> None:
        """Start the background reader for the opened FFmpeg process."""

        self.descriptor = descriptor
        self._process = process
        self._width = width
        self._height = height
        self._closed = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._latest_frame: PreviewFrame | None = None
        self._failure_reason: str | None = None
        self._frame_number = 0
        self._stderr_lines: deque[str] = deque(maxlen=8)
        self._stderr_reader = threading.Thread(
            target=self._stderr_loop,
            name=f"webcam-micro-stderr-{descriptor.stable_id}",
            daemon=True,
        )
        self._reader = threading.Thread(
            target=self._reader_loop,
            name=f"webcam-micro-camera-{descriptor.stable_id}",
            daemon=True,
        )
        self._stderr_reader.start()
        self._reader.start()

    def _stderr_loop(self) -> None:
        """Capture a small rolling stderr tail for readable failures."""

        stderr = self._process.stderr
        if stderr is None:
            return
        while not self._stop_event.is_set():
            raw_line = stderr.readline()
            if not raw_line:
                return
            line = raw_line.decode("utf-8", errors="replace").strip()
            if line:
                self._stderr_lines.append(line)

    def _read_exact(self, expected_bytes: int) -> bytes | None:
        """Read one raw frame payload or return `None` on EOF."""

        stdout = self._process.stdout
        if stdout is None:
            return None
        chunks: list[bytes] = []
        remaining = expected_bytes
        while remaining > 0 and not self._stop_event.is_set():
            chunk = stdout.read(remaining)
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining > 0:
            return None
        return b"".join(chunks)

    def _set_failure(self, message: str) -> None:
        """Record the first visible preview failure."""

        with self._lock:
            if self._failure_reason is None:
                self._failure_reason = message

    def _reader_loop(self) -> None:
        """Keep only the newest frame so preview does not lag behind motion."""

        expected_bytes = self._width * self._height * 3
        while not self._stop_event.is_set():
            payload = self._read_exact(expected_bytes)
            if payload is None:
                if self._stop_event.is_set():
                    return
                self._set_failure(self._build_failure_message())
                return
            self._frame_number += 1
            preview = PreviewFrame(
                width=self._width,
                height=self._height,
                rgb_bytes=payload,
                frame_number=self._frame_number,
            )
            with self._lock:
                self._latest_frame = preview

    def _build_failure_message(self) -> str:
        """Return the best visible message for an FFmpeg session failure."""

        if self._stderr_lines:
            return self._stderr_lines[-1]
        return "Camera preview stopped delivering frames."

    def get_latest_frame(self) -> PreviewFrame | None:
        """Return the newest captured frame, if one is available."""

        with self._lock:
            return self._latest_frame

    @property
    def failure_reason(self) -> str | None:
        """Return the current recoverable runtime failure, if any."""

        with self._lock:
            return self._failure_reason

    def close(self) -> None:
        """Stop the reader thread and release the FFmpeg process."""

        if self._closed:
            return
        self._closed = True
        self._stop_event.set()
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1.0)
        if self._reader.is_alive():
            self._reader.join(timeout=1.0)
        if self._stderr_reader.is_alive():
            self._stderr_reader.join(timeout=1.0)
        with contextlib.suppress(Exception):
            if self._process.stdout is not None:
                self._process.stdout.close()
        with contextlib.suppress(Exception):
            if self._process.stderr is not None:
                self._process.stderr.close()


class QtCameraBackend:
    """Discover cameras and open live preview sessions with Qt Multimedia."""

    backend_name = "qt_multimedia"

    def __init__(self) -> None:
        """Validate the Qt runtime backend and initialize controls."""

        (
            self._qt_core,
            self._qt_gui,
            self._qt_multimedia,
        ) = _load_qt_camera_modules()
        if (
            self._qt_core is None
            or self._qt_gui is None
            or self._qt_multimedia is None
        ):
            raise MissingCameraDependencyError(
                "Install the package runtime dependencies before opening a "
                "camera session."
            )
        if sys.platform == "darwin":
            control_backend = AvFoundationCameraControlBackend()
            if control_backend.available:
                self._control_backend: CameraControlBackend = control_backend
            else:
                self._control_backend = NullCameraControlBackend()
        else:
            self._control_backend = NullCameraControlBackend()

    def _camera_device_for_descriptor(
        self, descriptor: CameraDescriptor
    ) -> Any | None:
        """Return the Qt camera device matching one shared descriptor."""

        assert self._qt_multimedia is not None
        for index, device in enumerate(
            self._qt_multimedia.QMediaDevices.videoInputs()
        ):
            if (
                _qt_camera_stable_id(device, fallback_index=index)
                == descriptor.stable_id
            ):
                return device
            identifier = _qt_camera_identifier_text(bytes(device.id()))
            if (
                descriptor.native_identifier is not None
                and identifier == descriptor.native_identifier
            ):
                return device
        return None

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return the cameras Qt Multimedia can currently enumerate."""

        return _discover_qt_cameras()

    def open_session(self, descriptor: CameraDescriptor) -> QtCameraSession:
        """Open one Qt camera session for the provided descriptor."""

        camera_device = self._camera_device_for_descriptor(descriptor)
        if camera_device is None:
            raise RuntimeError(
                "The selected camera could not be found in the current Qt "
                "device list."
            )
        assert self._qt_gui is not None
        assert self._qt_core is not None
        assert self._qt_multimedia is not None
        return QtCameraSession(
            descriptor=descriptor,
            camera_device=camera_device,
            qt_core=self._qt_core,
            qt_gui=self._qt_gui,
            qt_multimedia=self._qt_multimedia,
        )

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the control surface for the selected camera."""

        return self._control_backend.list_controls(descriptor)

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one control value through the composed control backend."""

        self._control_backend.set_control_value(descriptor, control_id, value)

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one action control through the composed backend."""

        self._control_backend.trigger_control_action(
            descriptor,
            control_id,
        )


class FfmpegCameraBackend:
    """Discover cameras and open low-latency preview sessions with FFmpeg."""

    backend_name = "ffmpeg"
    preview_width = 640
    preview_height = 480

    def __init__(self) -> None:
        """Validate the runtime preview backend and initialize controls."""

        self._ffmpeg_exe = _ffmpeg_executable()
        if sys.platform == "darwin":
            control_backend = AvFoundationCameraControlBackend()
            if control_backend.available:
                self._control_backend: CameraControlBackend = control_backend
            else:
                self._control_backend = NullCameraControlBackend()
        else:
            self._control_backend = NullCameraControlBackend()

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return the cameras FFmpeg can currently enumerate."""

        return _discover_ffmpeg_cameras(self._ffmpeg_exe)

    def open_session(
        self, descriptor: CameraDescriptor
    ) -> FfmpegCameraSession:
        """Open one FFmpeg preview process for the provided camera."""

        command = [
            self._ffmpeg_exe,
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-probesize",
            "32",
            "-analyzeduration",
            "0",
            *_input_args(descriptor.device_selector),
            "-an",
            "-sn",
            "-vf",
            f"scale={self.preview_width}:{self.preview_height}",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "pipe:1",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        return FfmpegCameraSession(
            descriptor=descriptor,
            process=process,
            width=self.preview_width,
            height=self.preview_height,
        )

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the control surface for the selected camera."""

        return self._control_backend.list_controls(descriptor)

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one control value through the composed control backend."""

        self._control_backend.set_control_value(descriptor, control_id, value)

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one action control through the composed backend."""

        self._control_backend.trigger_control_action(
            descriptor,
            control_id,
        )
