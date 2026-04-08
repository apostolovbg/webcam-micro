"""Camera discovery, preview, and control backends for the prototype."""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.util
import errno
import glob
import math
import os
import re
import shutil
import subprocess
import sys
import threading
from collections import deque
from ctypes import c_bool
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from webcam_micro.error_reporting import WebcamMicroError

from .macos_permission import wrap_completion_handler


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


class CameraControlError(WebcamMicroError):
    """Raised when camera controls are unavailable or fail to apply."""


class CameraControlApplyError(CameraControlError):
    """Raised when one control value cannot be applied."""


class CameraOutputError(WebcamMicroError):
    """Raised when still or recording output work cannot complete."""


class CameraOpenError(CameraControlError):
    """Raised when a backend cannot open the selected camera session."""


class CameraSession(Protocol):
    """Represent one open camera session lifecycle."""

    def close(self) -> None:
        """Release backend resources for the active session."""

    def get_latest_frame(self) -> PreviewFrame | None:
        """Return the newest available preview frame."""

    @property
    def failure_reason(self) -> str | None:
        """Return the most recent recoverable session failure."""

    def start_recording(
        self,
        output_path: Path,
        *,
        crop_plan: RecordingCropPlan,
    ) -> Path:
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
class RecordingCropPlan:
    """Describe the frozen crop rectangle for one recording session."""

    source_x: int
    source_y: int
    source_width: int
    source_height: int


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
            "Qt Multimedia-backed discovery and live preview with one "
            "selected native device-control backend"
        ),
        notes=(
            "Stage 7 moves camera discovery and live preview onto Qt "
            "Multimedia camera devices and capture sessions.",
            "Preview readers keep only the newest frame surfaced through a "
            "QVideoSink so the workspace renderer does not lag behind live "
            "video.",
            "The typed control surface now selects one native device-control "
            "backend per camera so device-owned controls read real ranges, "
            "modes, and menu values.",
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

    def start_recording(
        self,
        output_path: Path,
        *,
        crop_plan: RecordingCropPlan,
    ) -> Path:
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


class MissingCameraDependencyError(WebcamMicroError):
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


def _permission_value(value: object) -> object:
    """Return one comparable scalar for a Qt or native permission status."""

    return getattr(value, "value", value)


def _camera_permission_denied_message() -> str:
    """Return one readable message for a denied camera permission."""

    if sys.platform == "darwin":
        return (
            "Camera access was denied. Open System Settings > Privacy & "
            "Security > Camera, allow the app or terminal, then relaunch."
        )
    return (
        "Camera access was denied. Open the system privacy settings and "
        "relaunch."
    )


def request_camera_permission(qt_core: Any) -> tuple[bool, str]:
    """Request camera permission through the native platform prompt."""

    if sys.platform == "darwin":
        return _request_macos_camera_permission(qt_core)
    return _request_qt_camera_permission(qt_core)


def _request_macos_camera_permission(qt_core: Any) -> tuple[bool, str]:
    """Request macOS camera permission through AVFoundation."""

    capture_device_class, media_type_video = _load_avfoundation_modules()
    if capture_device_class is None or media_type_video is None:
        return False, (
            "Camera access could not be requested because the macOS camera "
            "bridge is unavailable."
        )
    status = int(
        capture_device_class.authorizationStatusForMediaType_(media_type_video)
    )
    if status == 3:
        return True, ""
    if status in {1, 2}:
        return False, _camera_permission_denied_message()

    completion_loop = qt_core.QEventLoop()
    result = {"granted": False, "finished": False}

    def completion_handler(granted: c_bool) -> None:
        """Store the macOS permission result and stop waiting."""

        result["granted"] = bool(granted)
        result["finished"] = True
        completion_loop.quit()

    completion_handler = wrap_completion_handler(completion_handler)
    capture_device_class.requestAccessForMediaType_completionHandler_(
        media_type_video,
        completion_handler,
    )
    if not result["finished"]:
        getattr(completion_loop, "exec")()
    if result["granted"]:
        return True, ""
    return False, _camera_permission_denied_message()


def _request_qt_camera_permission(qt_core: Any) -> tuple[bool, str]:
    """Request Qt camera permission on non-macOS platforms."""

    permission_type = getattr(qt_core, "QCameraPermission", None)
    qcore_application = getattr(qt_core, "QCoreApplication", None)
    if permission_type is None or qcore_application is None:
        return True, ""
    application = getattr(qcore_application, "instance", None)
    if application is None:
        return True, ""
    app = application()
    if app is None:
        return True, ""
    permission = permission_type()
    try:
        current_status = app.checkPermission(permission)
    except (AttributeError, RuntimeError, TypeError):
        return True, ""
    permission_status = getattr(
        getattr(qt_core, "Qt", object()),
        "PermissionStatus",
        None,
    )
    granted_status = getattr(permission_status, "Granted", None)
    denied_status = getattr(permission_status, "Denied", None)
    if granted_status is not None and (
        _permission_value(current_status) == _permission_value(granted_status)
    ):
        return True, ""
    if denied_status is not None and (
        _permission_value(current_status) == _permission_value(denied_status)
    ):
        return False, _camera_permission_denied_message()

    completion_loop = qt_core.QEventLoop()
    result = {"granted": False, "finished": False}

    class PermissionReceiver(qt_core.QObject):
        """Collect the camera-permission callback result."""

        def __init__(self) -> None:
            """Initialize the permission callback receiver."""

            super().__init__()

        def on_permission(self, status: object) -> None:
            """Store the permission callback result and stop waiting."""

            result["granted"] = bool(
                _permission_value(status) == _permission_value(granted_status)
                if granted_status is not None
                else status
            )
            result["finished"] = True
            completion_loop.quit()

    receiver = PermissionReceiver()
    try:
        app.requestPermission(permission, receiver, receiver.on_permission)
    except (AttributeError, RuntimeError, TypeError):
        return True, ""
    if not result["finished"]:
        getattr(completion_loop, "exec")()
    if result["granted"]:
        return True, ""
    return False, _camera_permission_denied_message()


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


_RECORDING_FILE_FORMAT_SUFFIXES = {
    "AVI": (".avi",),
    "Matroska": (".mkv",),
    "MPEG4": (".mp4",),
    "Ogg": (".ogv", ".ogg"),
    "QuickTime": (".mov",),
    "WMV": (".wmv",),
    "WebM": (".webm",),
}
_PREFERRED_RECORDING_FILE_FORMAT_NAMES = (
    "MPEG4",
    "QuickTime",
    "Matroska",
    "WebM",
    "WMV",
    "AVI",
    "Ogg",
)


def _qt_media_file_format_name(file_format: object) -> str:
    """Return one stable enum name for a Qt media file format."""

    return (
        getattr(file_format, "name", "")
        or str(file_format).rsplit(
            ".",
            1,
        )[-1]
    )


def _qt_recording_file_format_entries(
    qt_multimedia: Any,
) -> tuple[tuple[object, tuple[str, ...], str], ...]:
    """Return the supported video recording containers for this runtime."""

    media_format_class = getattr(qt_multimedia, "QMediaFormat", None)
    if media_format_class is None:
        return ()
    file_format_enum = getattr(media_format_class, "FileFormat", None)
    conversion_mode_enum = getattr(media_format_class, "ConversionMode", None)
    if file_format_enum is None or conversion_mode_enum is None:
        return ()

    probe = media_format_class()
    try:
        supported_file_formats = tuple(
            probe.supportedFileFormats(conversion_mode_enum.Encode)
        )
    except (AttributeError, RuntimeError, TypeError):
        supported_file_formats = ()

    if supported_file_formats:
        candidates: tuple[object, ...] = supported_file_formats
    else:
        candidates = tuple(
            getattr(file_format_enum, name, None)
            for name in _PREFERRED_RECORDING_FILE_FORMAT_NAMES
        )

    entries_by_name: dict[str, tuple[object, tuple[str, ...], str]] = {}
    for file_format in candidates:
        if file_format is None:
            continue
        format_name = _qt_media_file_format_name(file_format)
        suffixes = _RECORDING_FILE_FORMAT_SUFFIXES.get(format_name)
        if suffixes is None or format_name in entries_by_name:
            continue
        if not supported_file_formats:
            try:
                probe.setFileFormat(file_format)
                if not probe.isSupported(conversion_mode_enum.Encode):
                    continue
            except (AttributeError, RuntimeError, TypeError):
                continue
        try:
            label = probe.fileFormatDescription(file_format)
        except (AttributeError, RuntimeError, TypeError):
            label = ""
        if not label:
            try:
                label = probe.fileFormatName(file_format)
            except (AttributeError, RuntimeError, TypeError):
                label = format_name
        entries_by_name[format_name] = (
            file_format,
            suffixes,
            str(label),
        )

    ordered_names = [
        name
        for name in _PREFERRED_RECORDING_FILE_FORMAT_NAMES
        if name in entries_by_name
    ]
    ordered_names.extend(
        sorted(name for name in entries_by_name if name not in ordered_names)
    )
    return tuple(entries_by_name[name] for name in ordered_names)


def build_recording_file_filter(qt_multimedia: Any) -> str:
    """Return one recording save filter tailored to supported formats."""

    entries = _qt_recording_file_format_entries(qt_multimedia)
    if not entries:
        return "Video Files (*.mp4)"
    filters = [
        f"{label} ({' '.join(f'*{suffix}' for suffix in suffixes)})"
        for _file_format, suffixes, label in entries
    ]
    return ";;".join(filters)


def _preferred_recording_output_suffix(qt_multimedia: Any) -> str:
    """Return one default recording suffix supported by this runtime."""

    entries = _qt_recording_file_format_entries(qt_multimedia)
    if not entries:
        return ".mp4"
    return entries[0][1][0]


def _qt_recording_output_path_for_path(
    path: Path,
    qt_multimedia: Any,
) -> tuple[Path, object]:
    """Return one normalized recording path and its Qt media format."""

    entries = _qt_recording_file_format_entries(qt_multimedia)
    if not entries:
        raise CameraOutputError(
            "No supported video recording containers are available on "
            "this platform."
        )
    format_by_suffix: dict[str, object] = {}
    for file_format, suffixes, _label in entries:
        for suffix in suffixes:
            format_by_suffix.setdefault(suffix, file_format)

    suffix = path.suffix.lower()
    if suffix:
        file_format = format_by_suffix.get(suffix)
        if file_format is None:
            supported_suffixes = ", ".join(sorted(format_by_suffix))
            raise CameraOutputError(
                f"Recording format `{suffix}` is not supported on this "
                f"platform. Supported video containers: {supported_suffixes}."
            )
        return path, file_format

    preferred_path, file_format = next(
        (
            (
                path.with_suffix(suffixes[0]),
                file_format,
            )
            for file_format, suffixes, _label in entries
        ),
        (path.with_suffix(".mp4"), entries[0][0]),
    )
    return preferred_path, file_format


def _qt_recorder_state_text(state: object, qt_multimedia: Any) -> str:
    """Return a readable recording-state label for one Qt enum value."""

    states = qt_multimedia.QMediaRecorder.RecorderState
    if state == states.RecordingState:
        return "recording"
    if state == states.PausedState:
        return "paused"
    return "stopped"


def _normalized_recording_crop_plan(
    crop_plan: RecordingCropPlan,
    *,
    source_width: int,
    source_height: int,
) -> RecordingCropPlan:
    """Clamp one recording crop rectangle to the current frame bounds."""

    bounded_x = min(max(0, int(crop_plan.source_x)), max(0, source_width - 1))
    bounded_y = min(
        max(0, int(crop_plan.source_y)),
        max(0, source_height - 1),
    )
    bounded_width = min(
        max(1, int(crop_plan.source_width)),
        max(1, source_width - bounded_x),
    )
    bounded_height = min(
        max(1, int(crop_plan.source_height)),
        max(1, source_height - bounded_y),
    )
    return RecordingCropPlan(
        source_x=bounded_x,
        source_y=bounded_y,
        source_width=bounded_width,
        source_height=bounded_height,
    )


def _crop_recording_qimage(image: Any, *, crop_plan: RecordingCropPlan) -> Any:
    """Return one frame-sized recording crop from the processed preview."""

    bounded_plan = _normalized_recording_crop_plan(
        crop_plan,
        source_width=int(image.width()),
        source_height=int(image.height()),
    )
    return image.copy(
        bounded_plan.source_x,
        bounded_plan.source_y,
        bounded_plan.source_width,
        bounded_plan.source_height,
    )


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


def _enum_name(value: object) -> str:
    """Return one stable enum or value name for a Qt control token."""

    name = getattr(value, "name", "")
    if name:
        return str(name)
    text = str(value)
    if "." in text:
        return text.rsplit(".", 1)[-1]
    return text


def _qt_camera_device_for_descriptor(
    qt_multimedia: Any,
    descriptor: CameraDescriptor,
) -> Any | None:
    """Return the Qt camera device that matches one shared descriptor."""

    if qt_multimedia is None:
        return None
    counts: dict[str, int] = {}
    for index, device in enumerate(qt_multimedia.QMediaDevices.videoInputs()):
        display_name = device.description() or f"Camera {index + 1}"
        occurrence_index = counts.get(display_name, 0)
        counts[display_name] = occurrence_index + 1
        stable_id = _qt_camera_stable_id(device, fallback_index=index)
        identifier = _qt_camera_identifier_text(bytes(device.id()))
        if stable_id == descriptor.stable_id:
            return device
        if (
            descriptor.native_identifier is not None
            and identifier == descriptor.native_identifier
        ):
            return device
        if (
            descriptor.display_name == display_name
            and descriptor.display_occurrence_index == occurrence_index
        ):
            return device
    return None


def _qcamera_feature_enabled(features: object, feature: object) -> bool:
    """Return whether one Qt camera feature flag is set."""

    try:
        return bool(features & feature)
    except TypeError:
        return False


def _qcamera_feature_supported(
    camera: Any,
    features: object,
    feature: object,
    *method_names: str,
) -> bool:
    """Return whether Qt reports one feature and exposes the needed methods."""

    if not _qcamera_feature_enabled(features, feature):
        return False
    for method_name in method_names:
        if getattr(camera, method_name, None) is None:
            return False
    return True


def _qcamera_choice_list(
    camera: Any,
    enum_cls: Any,
    support_method_name: str,
    specs: tuple[tuple[str, str, str], ...],
) -> tuple[CameraControlChoice, ...]:
    """Return the supported enum choices for one Qt camera control."""

    support_method = getattr(camera, support_method_name, None)
    if support_method is None:
        return ()
    choices: list[CameraControlChoice] = []
    for token, member_name, label in specs:
        member = getattr(enum_cls, member_name, None)
        if member is None:
            continue
        try:
            if not support_method(member):
                continue
        except (AttributeError, RuntimeError, TypeError, ValueError):
            continue
        choices.append(CameraControlChoice(value=token, label=label))
    return tuple(choices)


def _qcamera_choice_token(
    current_value: object,
    enum_cls: Any,
    specs: tuple[tuple[str, str, str], ...],
) -> str | None:
    """Return the stable token for one Qt camera enum value."""

    for token, member_name, _label in specs:
        member = getattr(enum_cls, member_name, None)
        if member is not None and current_value == member:
            return token
    return None


def _qcamera_choice_value(
    token: str,
    enum_cls: Any,
    specs: tuple[tuple[str, str, str], ...],
) -> object | None:
    """Return the Qt enum value for one stable camera token."""

    for spec_token, member_name, _label in specs:
        if spec_token == token:
            return getattr(enum_cls, member_name, None)
    return None


def _qcamera_camera_format_text(camera_format: object) -> str:
    """Return one readable summary for the active Qt camera format."""

    resolution = getattr(camera_format, "resolution", None)
    if callable(resolution):
        resolution = resolution()
    width = getattr(resolution, "width", lambda: None)()
    height = getattr(resolution, "height", lambda: None)()
    parts: list[str] = []
    if (
        isinstance(width, int)
        and isinstance(height, int)
        and width > 0
        and height > 0
    ):
        parts.append(f"{width}x{height}")
    pixel_format = getattr(camera_format, "pixelFormat", None)
    if callable(pixel_format):
        pixel_format = pixel_format()
    if pixel_format is not None:
        parts.append(_enum_name(pixel_format))
    min_frame_rate = _safe_float(
        getattr(camera_format, "minFrameRate", lambda: 0)()
    )
    max_frame_rate = _safe_float(
        getattr(camera_format, "maxFrameRate", lambda: 0)()
    )
    if min_frame_rate and max_frame_rate:
        if math.isclose(min_frame_rate, max_frame_rate, abs_tol=1e-6):
            parts.append(f"{max_frame_rate:g} fps")
        else:
            parts.append(f"{min_frame_rate:g}-{max_frame_rate:g} fps")
    elif max_frame_rate:
        parts.append(f"{max_frame_rate:g} fps")
    return ", ".join(parts) if parts else "Unknown camera format"


def _qcamera_camera_format_token(camera_format: object) -> str:
    """Return one stable token for a Qt camera format choice."""

    resolution = getattr(camera_format, "resolution", None)
    if callable(resolution):
        resolution = resolution()
    width = _call_or_value(getattr(resolution, "width", None))
    height = _call_or_value(getattr(resolution, "height", None))
    parts: list[str] = []
    try:
        width_value = int(width)
        height_value = int(height)
    except (TypeError, ValueError):
        width_value = None
        height_value = None
    if (
        width_value is not None
        and height_value is not None
        and width_value > 0
        and height_value > 0
    ):
        parts.append(f"{width_value}x{height_value}")
    pixel_format = getattr(camera_format, "pixelFormat", None)
    if callable(pixel_format):
        pixel_format = pixel_format()
    if pixel_format is not None:
        parts.append(_enum_name(pixel_format))
    min_frame_rate = _safe_float(
        getattr(camera_format, "minFrameRate", lambda: 0)()
    )
    max_frame_rate = _safe_float(
        getattr(camera_format, "maxFrameRate", lambda: 0)()
    )
    if min_frame_rate and max_frame_rate:
        if math.isclose(min_frame_rate, max_frame_rate, abs_tol=1e-6):
            parts.append(f"{max_frame_rate:g}fps")
        else:
            parts.append(f"{min_frame_rate:g}-{max_frame_rate:g}fps")
    elif max_frame_rate:
        parts.append(f"{max_frame_rate:g}fps")
    token = "|".join(parts)
    return token if token else _qcamera_camera_format_text(camera_format)


def _qcamera_supported_camera_formats(
    camera_device: object,
) -> tuple[object, ...]:
    """Return the camera formats exposed by one Qt camera device."""

    formats_method = getattr(camera_device, "videoFormats", None)
    if callable(formats_method):
        try:
            formats = tuple(formats_method())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            formats = ()
        if formats:
            return formats
    current_format = getattr(camera_device, "cameraFormat", None)
    if callable(current_format):
        try:
            active_format = current_format()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            active_format = None
        if active_format is not None:
            return (active_format,)
    return ()


def _qcamera_camera_format_choices(
    camera_device: object,
) -> tuple[CameraControlChoice, ...]:
    """Return the supported Qt camera-format choices for one device."""

    choices: list[CameraControlChoice] = []
    seen_tokens: set[str] = set()
    for camera_format in _qcamera_supported_camera_formats(camera_device):
        token = _qcamera_camera_format_token(camera_format)
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        choices.append(
            CameraControlChoice(
                value=token,
                label=_qcamera_camera_format_text(camera_format),
            )
        )
    return tuple(choices)


def _qcamera_camera_format_for_token(
    camera_device: object,
    token: str | None,
) -> object | None:
    """Return one Qt camera-format object for a stable choice token."""

    formats = _qcamera_supported_camera_formats(camera_device)
    if not formats:
        return None
    if token is None:
        return formats[0]
    for camera_format in formats:
        if _qcamera_camera_format_token(camera_format) == token:
            return camera_format
    return None


def _v4l2_normalize_text(text: str) -> str:
    """Return one lowercase snake-case token for a V4L2 control label."""

    return re.sub(r"[^0-9a-z]+", "_", text.lower()).strip("_")


def _v4l2_humanize_text(text: str) -> str:
    """Return one readable title-cased label for a V4L2 control name."""

    readable = re.sub(r"[^0-9A-Za-z]+", " ", text).strip()
    return readable.title() if readable else text


def _v4l2_menu_choice_token(label: str, *, value: int | None = None) -> str:
    """Return one stable token for a V4L2 menu item."""

    numeric = re.search(r"\d+", label)
    if numeric is not None:
        return numeric.group(0)
    if value is not None:
        return str(value)
    token = _v4l2_normalize_text(label)
    return token or label.lower()


def _ioctl_code(direction: int, type_char: str, number: int, size: int) -> int:
    """Return one Linux ioctl request code for a structured call."""

    ioctl_nrbits = 8
    ioctl_typebits = 8
    ioctl_sizebits = 14
    ioctl_dirbits = 2
    ioctl_nrshift = 0
    ioctl_typeshift = ioctl_nrshift + ioctl_nrbits
    ioctl_sizeshift = ioctl_typeshift + ioctl_typebits
    ioctl_dirshift = ioctl_sizeshift + ioctl_sizebits
    mask = (1 << ioctl_dirbits) - 1
    return (
        ((direction & mask) << ioctl_dirshift)
        | (ord(type_char) << ioctl_typeshift)
        | (number << ioctl_nrshift)
        | (size << ioctl_sizeshift)
    )


def _ioctl_readwrite(type_char: str, number: int, size: int) -> int:
    """Return one read-write ioctl request code."""

    return _ioctl_code(3, type_char, number, size)


class _V4L2Control(ctypes.Structure):
    """Represent one V4L2 control value payload."""

    _fields_ = [("id", ctypes.c_uint32), ("value", ctypes.c_int32)]


class _V4L2QueryCtrl(ctypes.Structure):
    """Represent one V4L2 control query payload."""

    _fields_ = [
        ("id", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("name", ctypes.c_uint8 * 32),
        ("minimum", ctypes.c_int32),
        ("maximum", ctypes.c_int32),
        ("step", ctypes.c_int32),
        ("default_value", ctypes.c_int32),
        ("flags", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 2),
    ]


class _V4L2QueryMenuValue(ctypes.Union):
    """Represent the union payload for one V4L2 menu item."""

    _fields_ = [
        ("name", ctypes.c_uint8 * 32),
        ("value", ctypes.c_int64),
    ]


class _V4L2QueryMenu(ctypes.Structure):
    """Represent one V4L2 menu-item query payload."""

    _pack_ = 1
    _fields_ = [
        ("id", ctypes.c_uint32),
        ("index", ctypes.c_uint32),
        ("payload", _V4L2QueryMenuValue),
        ("reserved", ctypes.c_uint32),
    ]


_V4L2_CTRL_TYPE_INTEGER = 1
_V4L2_CTRL_TYPE_BOOLEAN = 2
_V4L2_CTRL_TYPE_MENU = 3
_V4L2_CTRL_TYPE_BUTTON = 4
_V4L2_CTRL_TYPE_INTEGER64 = 5
_V4L2_CTRL_TYPE_CTRL_CLASS = 6
_V4L2_CTRL_TYPE_STRING = 7
_V4L2_CTRL_TYPE_BITMASK = 8
_V4L2_CTRL_TYPE_INTEGER_MENU = 9
_V4L2_CTRL_TYPE_U8 = 0x0100
_V4L2_CTRL_TYPE_U16 = 0x0101
_V4L2_CTRL_TYPE_U32 = 0x0102
_V4L2_CTRL_TYPE_AREA = 0x0106
_V4L2_CTRL_FLAG_DISABLED = 0x0001
_V4L2_CTRL_FLAG_READ_ONLY = 0x0004
_V4L2_CTRL_FLAG_WRITE_ONLY = 0x0040
_V4L2_CTRL_FLAG_EXECUTE_ON_WRITE = 0x0200
_V4L2_CTRL_FLAG_NEXT_CTRL = 0x80000000
_V4L2_CTRL_FLAG_NEXT_COMPOUND = 0x40000000
_V4L2_CID_PRIVATE_BASE = 0x08000000
_VIDIOC_G_CTRL = _ioctl_readwrite(
    "V",
    27,
    ctypes.sizeof(_V4L2Control),
)
_VIDIOC_S_CTRL = _ioctl_readwrite(
    "V",
    28,
    ctypes.sizeof(_V4L2Control),
)
_VIDIOC_QUERYCTRL = _ioctl_readwrite(
    "V",
    36,
    ctypes.sizeof(_V4L2QueryCtrl),
)
_VIDIOC_QUERYMENU = _ioctl_readwrite(
    "V",
    37,
    ctypes.sizeof(_V4L2QueryMenu),
)


def _v4l2_ioctl_struct(
    device_fd: int,
    request: int,
    struct_obj: object,
) -> object:
    """Run one V4L2 ioctl against a ctypes structure payload."""

    import fcntl

    struct_size = ctypes.sizeof(struct_obj)
    buffer = ctypes.create_string_buffer(struct_size)
    ctypes.memmove(buffer, ctypes.addressof(struct_obj), struct_size)
    fcntl.ioctl(device_fd, request, buffer, True)
    return type(struct_obj).from_buffer_copy(buffer)


def _v4l2_control_name(query: _V4L2QueryCtrl) -> str:
    """Return one readable label from a V4L2 control query."""

    raw_name = (
        bytes(query.name)
        .split(b"\0", 1)[0]
        .decode(
            "utf-8",
            errors="replace",
        )
    )
    return raw_name.strip()


def _v4l2_control_id(raw_name: str) -> str:
    """Return one stable control ID from a V4L2 control label."""

    normalized = _v4l2_normalize_text(raw_name)
    alias_map = {
        "auto_white_balance": "white_balance_automatic",
        "white_balance_auto": "white_balance_automatic",
        "white_balance_automatic": "white_balance_automatic",
        "white_balance_temperature": "white_balance_temperature",
        "backlight_compensation": "backlight_compensation",
        "power_line_frequency": "power_line_frequency",
        "auto_exposure": "exposure_mode",
        "exposure_auto": "exposure_mode",
    }
    return alias_map.get(normalized, normalized or "unknown_control")


@dataclass(frozen=True)
class _V4L2ControlRecord:
    """Describe one V4L2 control and its current value."""

    control_id: str
    label: str
    kind: str
    query_id: int
    value: object | None
    choices: tuple[CameraControlChoice, ...] = ()
    menu_values: tuple[int, ...] = ()
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    read_only: bool = False
    enabled: bool = True
    unit: str = ""
    details: str = ""
    action_label: str = ""


class _LibUVCInputTerminal(ctypes.Structure):
    """Describe one libuvc camera-terminal descriptor."""

    pass


class _LibUVCProcessingUnit(ctypes.Structure):
    """Describe one libuvc processing-unit descriptor."""

    pass


class _LibUVCExtensionUnit(ctypes.Structure):
    """Describe one libuvc extension-unit descriptor."""

    pass


_LibUVCInputTerminal._fields_ = [
    ("prev", ctypes.POINTER(_LibUVCInputTerminal)),
    ("next", ctypes.POINTER(_LibUVCInputTerminal)),
    ("bTerminalID", ctypes.c_uint8),
    ("wTerminalType", ctypes.c_uint16),
    ("wObjectiveFocalLengthMin", ctypes.c_uint16),
    ("wObjectiveFocalLengthMax", ctypes.c_uint16),
    ("wOcularFocalLength", ctypes.c_uint16),
    ("bmControls", ctypes.c_uint64),
]

_LibUVCProcessingUnit._fields_ = [
    ("prev", ctypes.POINTER(_LibUVCProcessingUnit)),
    ("next", ctypes.POINTER(_LibUVCProcessingUnit)),
    ("bUnitID", ctypes.c_uint8),
    ("bSourceID", ctypes.c_uint8),
    ("bmControls", ctypes.c_uint64),
]

_LibUVCExtensionUnit._fields_ = [
    ("prev", ctypes.POINTER(_LibUVCExtensionUnit)),
    ("next", ctypes.POINTER(_LibUVCExtensionUnit)),
    ("bUnitID", ctypes.c_uint8),
    ("guidExtensionCode", ctypes.c_uint8 * 16),
    ("bmControls", ctypes.c_uint64),
]


_LIBUVC_GET_CUR = 0x81
_LIBUVC_GET_MIN = 0x82
_LIBUVC_GET_MAX = 0x83
_LIBUVC_GET_RES = 0x84
_LIBUVC_GET_LEN = 0x85
_LIBUVC_GET_INFO = 0x86
_LIBUVC_GET_DEF = 0x87

_LIBUVC_CALL_ERRORS = (
    AttributeError,
    ctypes.ArgumentError,
    OSError,
    TypeError,
    ValueError,
)

_LIBUVC_CT_AE_MODE_CONTROL = 0x02
_LIBUVC_CT_AE_PRIORITY_CONTROL = 0x03
_LIBUVC_CT_EXPOSURE_TIME_ABSOLUTE_CONTROL = 0x04
_LIBUVC_CT_FOCUS_ABSOLUTE_CONTROL = 0x06
_LIBUVC_CT_FOCUS_AUTO_CONTROL = 0x08
_LIBUVC_CT_ZOOM_ABSOLUTE_CONTROL = 0x0B

_LIBUVC_PU_BACKLIGHT_COMPENSATION_CONTROL = 0x01
_LIBUVC_PU_BRIGHTNESS_CONTROL = 0x02
_LIBUVC_PU_CONTRAST_CONTROL = 0x03
_LIBUVC_PU_GAIN_CONTROL = 0x04
_LIBUVC_PU_POWER_LINE_FREQUENCY_CONTROL = 0x05
_LIBUVC_PU_HUE_CONTROL = 0x06
_LIBUVC_PU_SATURATION_CONTROL = 0x07
_LIBUVC_PU_SHARPNESS_CONTROL = 0x08
_LIBUVC_PU_GAMMA_CONTROL = 0x09
_LIBUVC_PU_WHITE_BALANCE_TEMPERATURE_CONTROL = 0x0A
_LIBUVC_PU_WHITE_BALANCE_TEMPERATURE_AUTO_CONTROL = 0x0B
_LIBUVC_PU_HUE_AUTO_CONTROL = 0x10
_LIBUVC_PU_CONTRAST_AUTO_CONTROL = 0x13


@dataclass(frozen=True)
class _LibUVCControlRecord:
    """Describe one libuvc-backed control and its current value."""

    control_id: str
    label: str
    kind: str
    unit_id: int
    selector: int
    getter_name: str
    setter_name: str
    value: object | None
    choices: tuple[CameraControlChoice, ...] = ()
    menu_values: tuple[int, ...] = ()
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    read_only: bool = False
    enabled: bool = True
    unit: str = ""
    details: str = ""
    action_label: str = ""
    scale: float = 1.0
    signed: bool = False
    size: int = 0


def _load_libuvc_library() -> object | None:
    """Return the libuvc shared library when it is installed."""

    candidates: list[str] = []
    found_path = ctypes.util.find_library("uvc")
    if found_path:
        candidates.append(found_path)
    candidates.extend(
        [
            "/usr/local/opt/libuvc/lib/libuvc.dylib",
            "/opt/homebrew/opt/libuvc/lib/libuvc.dylib",
            "/usr/local/lib/libuvc.dylib",
            "/opt/homebrew/lib/libuvc.dylib",
        ]
    )
    for candidate in candidates:
        if not candidate or not Path(candidate).exists():
            continue
        try:
            library = ctypes.CDLL(candidate)
        except OSError:
            continue
        _configure_libuvc_library(library)
        return library
    return None


def _configure_libuvc_library(library: object) -> None:
    """Install ctypes signatures for the libuvc functions we use."""

    def bind(
        name: str,
        restype: object,
        argtypes: tuple[object, ...],
    ) -> None:
        """Bind one libuvc symbol when the shared library exports it."""

        function = getattr(library, name, None)
        if function is None:
            return
        function.restype = restype
        function.argtypes = list(argtypes)

    bind(
        "uvc_init",
        ctypes.c_int,
        (ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p),
    )
    bind("uvc_exit", None, (ctypes.c_void_p,))
    bind(
        "uvc_get_device_list",
        ctypes.c_int,
        (ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))),
    )
    bind(
        "uvc_free_device_list",
        None,
        (ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint8),
    )
    bind(
        "uvc_get_device_descriptor",
        ctypes.c_int,
        (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.POINTER(_LibUVCDeviceDescriptor)),
        ),
    )
    bind(
        "uvc_free_device_descriptor",
        None,
        (ctypes.POINTER(_LibUVCDeviceDescriptor),),
    )
    bind(
        "uvc_open",
        ctypes.c_int,
        (ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)),
    )
    bind("uvc_close", None, (ctypes.c_void_p,))
    bind("uvc_ref_device", None, (ctypes.c_void_p,))
    bind("uvc_unref_device", None, (ctypes.c_void_p,))
    bind(
        "uvc_get_camera_terminal",
        ctypes.POINTER(_LibUVCInputTerminal),
        (ctypes.c_void_p,),
    )
    bind(
        "uvc_get_processing_units",
        ctypes.POINTER(_LibUVCProcessingUnit),
        (ctypes.c_void_p,),
    )
    bind(
        "uvc_get_extension_units",
        ctypes.POINTER(_LibUVCExtensionUnit),
        (ctypes.c_void_p,),
    )
    bind(
        "uvc_get_ctrl",
        ctypes.c_int,
        (
            ctypes.c_void_p,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
        ),
    )
    bind(
        "uvc_set_ctrl",
        ctypes.c_int,
        (
            ctypes.c_void_p,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_void_p,
            ctypes.c_int,
        ),
    )
    bind("uvc_strerror", ctypes.c_char_p, (ctypes.c_int,))

    for name, restype, argtypes in (
        (
            "uvc_get_ae_mode",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int),
        ),
        (
            "uvc_set_ae_mode",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint8),
        ),
        (
            "uvc_get_ae_priority",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int),
        ),
        (
            "uvc_set_ae_priority",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint8),
        ),
        (
            "uvc_get_exposure_abs",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_int),
        ),
        (
            "uvc_set_exposure_abs",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint32),
        ),
        (
            "uvc_get_focus_abs",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_focus_abs",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_focus_auto",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int),
        ),
        (
            "uvc_set_focus_auto",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint8),
        ),
        (
            "uvc_get_zoom_abs",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_zoom_abs",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_backlight_compensation",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_backlight_compensation",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_brightness",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_int),
        ),
        (
            "uvc_set_brightness",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_int16),
        ),
        (
            "uvc_get_contrast",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_contrast",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_contrast_auto",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int),
        ),
        (
            "uvc_set_contrast_auto",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint8),
        ),
        (
            "uvc_get_gain",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_gain",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_power_line_frequency",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int),
        ),
        (
            "uvc_set_power_line_frequency",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint8),
        ),
        (
            "uvc_get_hue",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_int),
        ),
        (
            "uvc_set_hue",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_int16),
        ),
        (
            "uvc_get_hue_auto",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int),
        ),
        (
            "uvc_set_hue_auto",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint8),
        ),
        (
            "uvc_get_saturation",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_saturation",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_sharpness",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_sharpness",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_gamma",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_gamma",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_white_balance_temperature",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_int),
        ),
        (
            "uvc_set_white_balance_temperature",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint16),
        ),
        (
            "uvc_get_white_balance_temperature_auto",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int),
        ),
        (
            "uvc_set_white_balance_temperature_auto",
            ctypes.c_int,
            (ctypes.c_void_p, ctypes.c_uint8),
        ),
    ):
        bind(name, restype, argtypes)


class _LibUVCDeviceDescriptor(ctypes.Structure):
    """Describe one libuvc device descriptor."""

    _fields_ = [
        ("idVendor", ctypes.c_uint16),
        ("idProduct", ctypes.c_uint16),
        ("bcdUVC", ctypes.c_uint16),
        ("serialNumber", ctypes.c_char_p),
        ("manufacturer", ctypes.c_char_p),
        ("product", ctypes.c_char_p),
    ]


def _libuvc_text(value: object | None) -> str | None:
    """Return a normalized text value from one libuvc string pointer."""

    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            text = bytes(value).decode("utf-8", errors="replace").strip()
        except UnicodeDecodeError:
            text = ""
        return text or None
    text = str(value).strip()
    return text or None


def _settings_text(value: object | None) -> str | None:
    """Return one normalized text value for settings tokens and labels."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _camera_identity_text(value: object | None) -> str | None:
    """Return one normalized identity token for camera matching."""

    text = _settings_text(value)
    if text is None:
        return None
    match = re.search(r"\s*\(([^()]*)\)\s*$", text)
    if match and "default" in match.group(1).casefold():
        text = text[: match.start()].rstrip()
    if not text:
        return None
    identity = re.sub(r"[^0-9a-z]+", " ", text.casefold())
    identity = " ".join(identity.split())
    return identity or None


def _libuvc_control_supported(bitmask: int, selector: int) -> bool:
    """Return whether one UVC selector bit is present in the bitmap."""

    if selector <= 0:
        return False
    return bool(bitmask & (1 << (selector - 1)))


def _v4l2_querymenu_item(
    device_fd: int,
    control_id: int,
    index: int,
) -> _V4L2QueryMenu | None:
    """Return one V4L2 menu item when the device exposes it."""

    query = _V4L2QueryMenu()
    query.id = control_id
    query.index = index
    try:
        return _v4l2_ioctl_struct(device_fd, _VIDIOC_QUERYMENU, query)
    except OSError as exc:
        if exc.errno in {errno.EINVAL, errno.ENOENT, errno.ENOTTY}:
            return None
        raise


def _v4l2_control_value(
    device_fd: int,
    query_id: int,
) -> int | None:
    """Return one integer V4L2 control value when readable."""

    control = _V4L2Control()
    control.id = query_id
    try:
        current = _v4l2_ioctl_struct(device_fd, _VIDIOC_G_CTRL, control)
    except OSError as exc:
        if exc.errno in {errno.EINVAL, errno.ENOENT, errno.ENOTTY}:
            return None
        raise
    return int(getattr(current, "value", 0))


def _v4l2_write_control_value(
    device_fd: int,
    query_id: int,
    value: int,
) -> None:
    """Write one integer V4L2 control value."""

    control = _V4L2Control()
    control.id = query_id
    control.value = int(value)
    _v4l2_ioctl_struct(device_fd, _VIDIOC_S_CTRL, control)


def _v4l2_control_record_from_query(
    device_fd: int,
    query: _V4L2QueryCtrl,
) -> _V4L2ControlRecord | None:
    """Return one typed V4L2 control record for the current query."""

    raw_name = _v4l2_control_name(query)
    if not raw_name:
        return None
    if query.type == _V4L2_CTRL_TYPE_CTRL_CLASS:
        return None
    if query.flags & _V4L2_CTRL_FLAG_DISABLED:
        return None
    control_id = _v4l2_control_id(raw_name)
    label = _v4l2_humanize_text(raw_name)
    details = f"Linux V4L2 control `{raw_name}`."
    read_only = bool(query.flags & _V4L2_CTRL_FLAG_READ_ONLY)
    enabled = not read_only and not bool(
        query.flags & _V4L2_CTRL_FLAG_WRITE_ONLY
    )
    if query.flags & _V4L2_CTRL_FLAG_EXECUTE_ON_WRITE:
        record_value = None
        return _V4L2ControlRecord(
            control_id=control_id,
            label=label,
            kind="action",
            query_id=int(query.id),
            value=record_value,
            read_only=False,
            enabled=enabled,
            details=details,
            action_label="Run",
        )
    if query.type == _V4L2_CTRL_TYPE_BUTTON:
        return _V4L2ControlRecord(
            control_id=control_id,
            label=label,
            kind="action",
            query_id=int(query.id),
            value=None,
            read_only=False,
            enabled=enabled,
            details=details,
            action_label="Run",
        )
    if query.type == _V4L2_CTRL_TYPE_BOOLEAN:
        current_value = _v4l2_control_value(device_fd, int(query.id))
        if current_value is None:
            current_value = int(query.default_value)
        return _V4L2ControlRecord(
            control_id=control_id,
            label=label,
            kind="boolean",
            query_id=int(query.id),
            value=bool(current_value),
            read_only=read_only,
            enabled=enabled,
            details=details,
        )
    if query.type in {_V4L2_CTRL_TYPE_MENU, _V4L2_CTRL_TYPE_INTEGER_MENU}:
        menu_choices: list[CameraControlChoice] = []
        menu_values: list[int] = []
        for index in range(int(query.minimum), int(query.maximum) + 1):
            menu_item = _v4l2_querymenu_item(
                device_fd,
                int(query.id),
                index,
            )
            if menu_item is None:
                continue
            if query.type == _V4L2_CTRL_TYPE_MENU:
                menu_label = (
                    bytes(menu_item.payload.name)
                    .split(
                        b"\0",
                        1,
                    )[0]
                    .decode("utf-8", errors="replace")
                    .strip()
                )
                if not menu_label:
                    continue
                menu_value = index
                token = _v4l2_menu_choice_token(menu_label)
            else:
                menu_value = int(menu_item.payload.value)
                menu_label = (
                    bytes(menu_item.payload.name)
                    .split(
                        b"\0",
                        1,
                    )[0]
                    .decode("utf-8", errors="replace")
                    .strip()
                )
                if not menu_label:
                    menu_label = str(menu_value)
                token = str(menu_value)
            menu_choices.append(
                CameraControlChoice(value=token, label=menu_label)
            )
            menu_values.append(menu_value)
        current_value = _v4l2_control_value(device_fd, int(query.id))
        current_token = None
        if current_value is not None:
            for choice, menu_value in zip(menu_choices, menu_values):
                if menu_value == current_value:
                    current_token = choice.value
                    break
        if current_token is None:
            current_token = menu_choices[0].value if menu_choices else "0"
        return _V4L2ControlRecord(
            control_id=control_id,
            label=label,
            kind="enum",
            query_id=int(query.id),
            value=current_token,
            choices=tuple(menu_choices),
            menu_values=tuple(menu_values),
            read_only=read_only,
            enabled=enabled,
            details=details,
        )
    if query.type in {
        _V4L2_CTRL_TYPE_INTEGER,
        _V4L2_CTRL_TYPE_INTEGER64,
        _V4L2_CTRL_TYPE_BITMASK,
        _V4L2_CTRL_TYPE_U8,
        _V4L2_CTRL_TYPE_U16,
        _V4L2_CTRL_TYPE_U32,
    }:
        current_value = _v4l2_control_value(device_fd, int(query.id))
        if current_value is None:
            current_value = int(query.default_value)
        minimum = float(query.minimum)
        maximum = float(query.maximum)
        step = float(query.step or 1)
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        if step <= 0:
            step = 1.0
        return _V4L2ControlRecord(
            control_id=control_id,
            label=label,
            kind="numeric",
            query_id=int(query.id),
            value=current_value,
            min_value=minimum,
            max_value=maximum,
            step=step,
            read_only=read_only,
            enabled=enabled,
            unit="",
            details=details,
        )
    return _V4L2ControlRecord(
        control_id=control_id,
        label=label,
        kind="read_only",
        query_id=int(query.id),
        value=raw_name,
        read_only=True,
        enabled=False,
        details=details,
    )


def _v4l2_records_for_device_path(
    device_path: str,
) -> tuple[_V4L2ControlRecord, ...]:
    """Return all V4L2 control records for one camera device node."""

    if not sys.platform.startswith("linux"):
        return ()
    try:
        device_fd = os.open(device_path, os.O_RDONLY)
    except OSError:
        return ()
    try:
        records: list[_V4L2ControlRecord] = []
        query = _V4L2QueryCtrl()
        query.id = _V4L2_CTRL_FLAG_NEXT_CTRL
        seen_ids: set[int] = set()
        while True:
            try:
                current = _v4l2_ioctl_struct(
                    device_fd,
                    _VIDIOC_QUERYCTRL,
                    query,
                )
            except OSError as exc:
                if exc.errno in {errno.EINVAL, errno.ENOENT, errno.ENOTTY}:
                    break
                raise
            control_id = int(current.id)
            if control_id in seen_ids:
                break
            seen_ids.add(control_id)
            if current.type == _V4L2_CTRL_TYPE_CTRL_CLASS:
                query.id = control_id | _V4L2_CTRL_FLAG_NEXT_CTRL
                continue
            record = _v4l2_control_record_from_query(device_fd, current)
            if record is not None:
                records.append(record)
            query.id = control_id | _V4L2_CTRL_FLAG_NEXT_CTRL
        return tuple(records)
    finally:
        os.close(device_fd)


def _v4l2_device_path_for_descriptor(
    descriptor: CameraDescriptor,
) -> str | None:
    """Return the Linux video-node path matching one shared descriptor."""

    if not sys.platform.startswith("linux"):
        return None
    device_selector = str(descriptor.device_selector).strip()
    if device_selector.startswith("/dev/video"):
        return device_selector
    counts: dict[str, int] = {}
    for device_path in sorted(glob.glob("/dev/video*")):
        device_name = Path(device_path).name
        sysfs_name = Path("/sys/class/video4linux") / device_name / "name"
        if not sysfs_name.exists():
            continue
        label = sysfs_name.read_text(encoding="utf-8").strip()
        if not label:
            continue
        occurrence_index = counts.get(label, 0)
        counts[label] = occurrence_index + 1
        if (
            label == descriptor.display_name
            and occurrence_index == descriptor.display_occurrence_index
        ):
            return device_path
    return None


class _SelectedCameraControlBackend:
    """Select one control backend per camera and delegate all access."""

    def __init__(self, *control_backends: CameraControlBackend) -> None:
        """Store control-backend candidates in priority order."""

        self._control_backends = tuple(control_backends)
        self._null_backend = NullCameraControlBackend()
        self._selected_backend_by_descriptor: dict[
            str, CameraControlBackend
        ] = {}

    def _backend_for_descriptor(
        self,
        descriptor: CameraDescriptor,
    ) -> CameraControlBackend:
        """Return the single control backend chosen for one camera."""

        selected_backend = self._selected_backend_by_descriptor.get(
            descriptor.stable_id
        )
        if selected_backend is not None:
            return selected_backend
        for backend in self._control_backends:
            try:
                controls = backend.list_controls(descriptor)
            except CameraControlError:
                continue
            if not controls:
                continue
            self._selected_backend_by_descriptor[descriptor.stable_id] = (
                backend
            )
            return backend
        return self._null_backend

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the selected control surface for one camera."""

        backend = self._backend_for_descriptor(descriptor)
        return backend.list_controls(descriptor)

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one control value through the selected backend."""

        backend = self._backend_for_descriptor(descriptor)
        backend.set_control_value(descriptor, control_id, value)

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one action through the selected backend."""

        backend = self._backend_for_descriptor(descriptor)
        backend.trigger_control_action(descriptor, control_id)


class LinuxV4L2CameraControlBackend:
    """Expose Linux V4L2 controls when the device node is available."""

    def __init__(
        self,
        device_path_for_descriptor: Callable[[CameraDescriptor], str | None],
    ) -> None:
        """Store the descriptor-to-device resolver used for V4L2 access."""

        self._device_path_for_descriptor = device_path_for_descriptor

    def _device_path(self, descriptor: CameraDescriptor) -> str | None:
        """Return the Linux device-node path for one shared descriptor."""

        return self._device_path_for_descriptor(descriptor)

    def _records_for_descriptor(
        self,
        descriptor: CameraDescriptor,
    ) -> tuple[_V4L2ControlRecord, ...]:
        """Return every readable V4L2 control record for one descriptor."""

        device_path = self._device_path(descriptor)
        if device_path is None:
            return ()
        return _v4l2_records_for_device_path(device_path)

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the V4L2 control surface for the selected camera."""

        controls: list[CameraControl] = []
        for record in self._records_for_descriptor(descriptor):
            controls.append(
                CameraControl(
                    control_id=record.control_id,
                    label=record.label,
                    kind=record.kind,
                    value=record.value,
                    choices=record.choices,
                    min_value=record.min_value,
                    max_value=record.max_value,
                    step=record.step,
                    read_only=record.read_only,
                    enabled=record.enabled,
                    unit=record.unit,
                    details=record.details,
                    action_label=record.action_label,
                )
            )
        return tuple(controls)

    def _record_for_control_id(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> _V4L2ControlRecord | None:
        """Return the V4L2 control record for one control ID."""

        for record in self._records_for_descriptor(descriptor):
            if record.control_id == control_id:
                return record
        return None

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one V4L2 control value."""

        device_path = self._device_path(descriptor)
        if device_path is None:
            raise CameraControlApplyError(
                "The selected camera could not be found for control updates."
            )
        record = self._record_for_control_id(descriptor, control_id)
        if record is None:
            raise CameraControlApplyError(
                f"Unsupported camera control `{control_id}`."
            )
        if record.read_only:
            raise CameraControlApplyError(
                f"The control `{control_id}` is read-only."
            )
        try:
            device_fd = os.open(device_path, os.O_RDWR)
        except OSError as exc:
            raise CameraControlApplyError(str(exc)) from exc
        try:
            if record.kind == "boolean":
                _v4l2_write_control_value(
                    device_fd,
                    record.query_id,
                    int(bool(value)),
                )
                return
            if record.kind == "numeric":
                numeric_value = _safe_float(value)
                if numeric_value is None:
                    raise CameraControlApplyError(
                        f"The control `{control_id}` must be numeric."
                    )
                _v4l2_write_control_value(
                    device_fd,
                    record.query_id,
                    int(round(numeric_value)),
                )
                return
            if record.kind == "enum":
                token = str(value).strip()
                if not token:
                    raise CameraControlApplyError(
                        "The control "
                        f"`{control_id}` must be set to one option."
                    )
                for choice, menu_value in zip(
                    record.choices,
                    record.menu_values,
                ):
                    if choice.value == token:
                        _v4l2_write_control_value(
                            device_fd,
                            record.query_id,
                            menu_value,
                        )
                        return
                raise CameraControlApplyError(
                    f"Unsupported menu choice `{token}` for `{control_id}`."
                )
            if record.kind == "action":
                _v4l2_write_control_value(device_fd, record.query_id, 1)
                return
            raise CameraControlApplyError(
                f"Unsupported camera control `{control_id}`."
            )
        finally:
            os.close(device_fd)

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one V4L2 action control."""

        record = self._record_for_control_id(descriptor, control_id)
        if record is None or record.kind != "action":
            raise CameraControlApplyError(
                f"Unsupported action control `{control_id}`."
            )
        self.set_control_value(descriptor, control_id, True)


class LibUVCControlBackend:
    """Expose native UVC camera controls through libuvc when available."""

    backend_name = "libuvc"

    def __init__(self, library: object | None = None) -> None:
        """Store the libuvc bindings and initialize a shared context."""

        self._lib = library if library is not None else _load_libuvc_library()
        self._context: object | None = None
        self._handle: object | None = None
        if self._lib is not None:
            self._context = self._create_context()

    @property
    def available(self) -> bool:
        """Return whether the native UVC bridge is ready."""

        return self._lib is not None and self._context is not None

    def __del__(self) -> None:
        """Release the shared libuvc context when the backend is collected."""

        context = self._context
        library = self._lib
        self._context = None
        if context is None or library is None:
            return
        with contextlib.suppress(*_LIBUVC_CALL_ERRORS):
            library.uvc_exit(context)

    def _create_context(self) -> object | None:
        """Return one initialized libuvc context when possible."""

        if self._lib is None:
            return None
        context = ctypes.c_void_p()
        try:
            result_code = self._lib.uvc_init(ctypes.byref(context), None)
        except _LIBUVC_CALL_ERRORS:
            return None
        if result_code != 0:
            return None
        return context

    def _uvc_error_text(self, error_code: int) -> str:
        """Return one readable libuvc error message."""

        if self._lib is None:
            return "The native UVC bridge is unavailable."
        strerror = getattr(self._lib, "uvc_strerror", None)
        if strerror is None:
            return f"libuvc error {error_code}."
        try:
            message = strerror(error_code)
        except _LIBUVC_CALL_ERRORS:
            return f"libuvc error {error_code}."
        text = _libuvc_text(message)
        if text is None:
            return f"libuvc error {error_code}."
        return text

    def _device_list(self) -> tuple[object, object | None] | tuple[None, None]:
        """Return one libuvc device list and its matching context."""

        if self._lib is None or self._context is None:
            return None, None
        device_list = ctypes.POINTER(ctypes.c_void_p)()
        try:
            result_code = self._lib.uvc_get_device_list(
                self._context,
                ctypes.byref(device_list),
            )
        except _LIBUVC_CALL_ERRORS:
            return None, None
        if result_code != 0 or not device_list:
            return None, None
        return device_list, self._context

    def _free_device_list(self, device_list: object | None) -> None:
        """Release one libuvc device list."""

        if self._lib is None or device_list is None:
            return
        with contextlib.suppress(*_LIBUVC_CALL_ERRORS):
            self._lib.uvc_free_device_list(device_list, 1)

    def _device_descriptor(
        self,
        device: object,
    ) -> _LibUVCDeviceDescriptor | None:
        """Return the descriptor for one libuvc device when possible."""

        if self._lib is None:
            return None
        descriptor = ctypes.POINTER(_LibUVCDeviceDescriptor)()
        try:
            result_code = self._lib.uvc_get_device_descriptor(
                device,
                ctypes.byref(descriptor),
            )
        except _LIBUVC_CALL_ERRORS:
            return None
        if result_code != 0 or not descriptor:
            return None
        return descriptor.contents

    def _free_device_descriptor(
        self,
        descriptor: _LibUVCDeviceDescriptor | None,
    ) -> None:
        """Release one libuvc device descriptor."""

        if self._lib is None or descriptor is None:
            return
        with contextlib.suppress(*_LIBUVC_CALL_ERRORS):
            self._lib.uvc_free_device_descriptor(ctypes.pointer(descriptor))

    def _device_label(self, descriptor: _LibUVCDeviceDescriptor) -> str:
        """Return one stable label for a libuvc device descriptor."""

        manufacturer = _libuvc_text(descriptor.manufacturer)
        product = _libuvc_text(descriptor.product)
        if manufacturer and product:
            return f"{manufacturer} {product}"
        if product:
            return product
        if manufacturer:
            return manufacturer
        return "UVC camera"

    def _device_matches_descriptor(
        self,
        device_descriptor: _LibUVCDeviceDescriptor,
        descriptor: CameraDescriptor,
        occurrence_index: int,
    ) -> bool:
        """Return whether one libuvc device matches a shared descriptor."""

        serial_number = _libuvc_text(device_descriptor.serialNumber)
        if (
            descriptor.native_identifier is not None
            and serial_number is not None
            and descriptor.native_identifier == serial_number
        ):
            return True
        device_label = self._device_label(device_descriptor)
        product = _libuvc_text(device_descriptor.product)
        manufacturer = _libuvc_text(device_descriptor.manufacturer)
        candidate_identities = {
            _camera_identity_text(device_label),
            _camera_identity_text(product),
            _camera_identity_text(manufacturer),
            _camera_identity_text(
                f"{manufacturer} {product}"
                if manufacturer and product
                else None
            ),
        }
        descriptor_identity = _camera_identity_text(descriptor.display_name)
        if descriptor_identity is not None and descriptor_identity in {
            identity for identity in candidate_identities if identity
        }:
            return occurrence_index == descriptor.display_occurrence_index
        return False

    def _device_for_descriptor(
        self,
        descriptor: CameraDescriptor,
    ) -> object | None:
        """Return the libuvc device that matches one shared descriptor."""

        device_list, _context = self._device_list()
        if device_list is None:
            return None
        try:
            seen_labels: dict[str, int] = {}
            index = 0
            while True:
                device = device_list[index]
                if not device:
                    break
                device_descriptor = self._device_descriptor(device)
                if device_descriptor is None:
                    index += 1
                    continue
                label = self._device_label(device_descriptor)
                occurrence_index = seen_labels.get(label, 0)
                seen_labels[label] = occurrence_index + 1
                if self._device_matches_descriptor(
                    device_descriptor,
                    descriptor,
                    occurrence_index,
                ):
                    with contextlib.suppress(*_LIBUVC_CALL_ERRORS):
                        self._lib.uvc_ref_device(device)
                    return device
                index += 1
        finally:
            self._free_device_list(device_list)
        return None

    def _open_device_handle(self, device: object) -> object | None:
        """Return one opened libuvc device handle when possible."""

        if self._lib is None:
            return None
        handle = ctypes.c_void_p()
        try:
            result_code = self._lib.uvc_open(device, ctypes.byref(handle))
        except _LIBUVC_CALL_ERRORS:
            return None
        finally:
            with contextlib.suppress(*_LIBUVC_CALL_ERRORS):
                self._lib.uvc_unref_device(device)
        if result_code != 0:
            return None
        return handle

    def _close_device_handle(self, handle: object | None) -> None:
        """Close one opened libuvc device handle."""

        if self._lib is None or handle is None:
            return
        with contextlib.suppress(*_LIBUVC_CALL_ERRORS):
            self._lib.uvc_close(handle)

    def _typed_request(
        self,
        getter_name: str,
        handle: object,
        value_type: object,
        req_code: int,
    ) -> object | None:
        """Return one typed libuvc value when the request succeeds."""

        if self._lib is None:
            return None
        getter = getattr(self._lib, getter_name, None)
        if getter is None:
            return None
        value = value_type()
        try:
            result_code = getter(handle, ctypes.byref(value), req_code)
        except _LIBUVC_CALL_ERRORS:
            return None
        if result_code != 0:
            return None
        return value.value

    def _raw_request(
        self,
        handle: object,
        unit_id: int,
        selector: int,
        req_code: int,
        size: int,
    ) -> bytes | None:
        """Return one raw libuvc control payload when possible."""

        if self._lib is None or size <= 0:
            return None
        getter = getattr(self._lib, "uvc_get_ctrl", None)
        if getter is None:
            return None
        payload = (ctypes.c_uint8 * size)()
        try:
            result_code = getter(
                handle,
                unit_id,
                selector,
                payload,
                size,
                req_code,
            )
        except _LIBUVC_CALL_ERRORS:
            return None
        if result_code != 0:
            return None
        return bytes(payload)

    def _raw_write(
        self,
        handle: object,
        unit_id: int,
        selector: int,
        payload: bytes,
    ) -> None:
        """Write one raw libuvc control payload."""

        if self._lib is None:
            raise CameraControlApplyError(
                "The native UVC bridge is unavailable."
            )
        setter = getattr(self._lib, "uvc_set_ctrl", None)
        if setter is None:
            raise CameraControlApplyError(
                "The native UVC bridge does not support raw controls."
            )
        buffer = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload)
        try:
            result_code = setter(
                handle, unit_id, selector, buffer, len(payload)
            )
        except _LIBUVC_CALL_ERRORS as exc:
            raise CameraControlApplyError(str(exc)) from exc
        if result_code != 0:
            raise CameraControlApplyError(self._uvc_error_text(result_code))

    def _numeric_record(
        self,
        *,
        control_id: str,
        label: str,
        getter_name: str,
        setter_name: str,
        unit_id: int,
        selector: int,
        value_type: object,
        unit: str = "",
        scale: float = 1.0,
        signed: bool = False,
        details: str = "",
    ) -> _LibUVCControlRecord | None:
        """Return one numeric libuvc record when the control is readable."""

        if self._lib is None:
            return None
        current = self._typed_request(
            getter_name, self._handle, value_type, _LIBUVC_GET_CUR
        )
        if current is None:
            current = self._typed_request(
                getter_name,
                self._handle,
                value_type,
                _LIBUVC_GET_DEF,
            )
        if current is None:
            return None
        minimum = self._typed_request(
            getter_name,
            self._handle,
            value_type,
            _LIBUVC_GET_MIN,
        )
        maximum = self._typed_request(
            getter_name,
            self._handle,
            value_type,
            _LIBUVC_GET_MAX,
        )
        resolution = self._typed_request(
            getter_name,
            self._handle,
            value_type,
            _LIBUVC_GET_RES,
        )

        def scaled(value: object | None) -> float | None:
            """Return one libuvc numeric value converted into control units."""

            if value is None:
                return None
            return _safe_float(value) * scale

        current_value = scaled(current)
        if current_value is None:
            return None
        minimum_value = scaled(minimum)
        maximum_value = scaled(maximum)
        if minimum_value is None and maximum_value is None:
            minimum_value = current_value
            maximum_value = current_value
        if minimum_value is not None and maximum_value is not None:
            current_value = max(
                minimum_value, min(maximum_value, current_value)
            )
        step = None
        if resolution is not None:
            step = max(_safe_float(resolution) * scale, 0.01)
        elif minimum_value is not None and maximum_value is not None:
            step = _numeric_step(minimum_value, maximum_value)
        return _LibUVCControlRecord(
            control_id=control_id,
            label=label,
            kind="numeric",
            unit_id=unit_id,
            selector=selector,
            getter_name=getter_name,
            setter_name=setter_name,
            value=current_value,
            min_value=minimum_value,
            max_value=maximum_value,
            step=step,
            unit=unit,
            details=details,
            scale=scale,
            signed=signed,
        )

    def _boolean_record(
        self,
        *,
        control_id: str,
        label: str,
        getter_name: str,
        setter_name: str,
        unit_id: int,
        selector: int,
        details: str = "",
    ) -> _LibUVCControlRecord | None:
        """Return one boolean libuvc record when the control is readable."""

        current = self._typed_request(
            getter_name,
            self._handle,
            ctypes.c_uint8,
            _LIBUVC_GET_CUR,
        )
        if current is None:
            current = self._typed_request(
                getter_name,
                self._handle,
                ctypes.c_uint8,
                _LIBUVC_GET_DEF,
            )
        if current is None:
            return None
        return _LibUVCControlRecord(
            control_id=control_id,
            label=label,
            kind="boolean",
            unit_id=unit_id,
            selector=selector,
            getter_name=getter_name,
            setter_name=setter_name,
            value=bool(current),
            details=details,
        )

    def _power_line_frequency_record(
        self,
        unit_id: int,
        selector: int,
    ) -> _LibUVCControlRecord | None:
        """Return the power-line frequency selector when available."""

        current = self._typed_request(
            "uvc_get_power_line_frequency",
            self._handle,
            ctypes.c_uint8,
            _LIBUVC_GET_CUR,
        )
        if current is None:
            current = self._typed_request(
                "uvc_get_power_line_frequency",
                self._handle,
                ctypes.c_uint8,
                _LIBUVC_GET_DEF,
            )
        if current is None:
            return None
        minimum = self._typed_request(
            "uvc_get_power_line_frequency",
            self._handle,
            ctypes.c_uint8,
            _LIBUVC_GET_MIN,
        )
        maximum = self._typed_request(
            "uvc_get_power_line_frequency",
            self._handle,
            ctypes.c_uint8,
            _LIBUVC_GET_MAX,
        )
        step = self._typed_request(
            "uvc_get_power_line_frequency",
            self._handle,
            ctypes.c_uint8,
            _LIBUVC_GET_RES,
        )
        if minimum is None:
            minimum = 0
        if maximum is None:
            maximum = max(minimum, 3)
        if step is None or step <= 0:
            step = 1
        choices: list[CameraControlChoice] = []
        menu_values: list[int] = []
        token_labels = {
            0: ("disabled", "Disabled"),
            1: ("50", "50 Hz"),
            2: ("60", "60 Hz"),
            3: ("auto", "Auto"),
        }
        for menu_value in range(int(minimum), int(maximum) + 1, int(step)):
            token, label = token_labels.get(
                menu_value, (str(menu_value), str(menu_value))
            )
            choices.append(CameraControlChoice(value=token, label=label))
            menu_values.append(menu_value)
        current_token = choices[0].value if choices else str(int(current))
        for choice, menu_value in zip(choices, menu_values):
            if menu_value == int(current):
                current_token = choice.value
                break
        return _LibUVCControlRecord(
            control_id="power_line_frequency",
            label="Power Line Frequency",
            kind="enum",
            unit_id=unit_id,
            selector=selector,
            getter_name="uvc_get_power_line_frequency",
            setter_name="uvc_set_power_line_frequency",
            value=current_token,
            choices=tuple(choices),
            menu_values=tuple(menu_values),
            min_value=float(minimum),
            max_value=float(maximum),
            step=float(step),
            details="UVC power-line frequency selector.",
        )

    def _camera_terminal_controls(
        self,
        camera_terminal: _LibUVCInputTerminal,
    ) -> tuple[_LibUVCControlRecord, ...]:
        """Return the camera-terminal controls exposed by libuvc."""

        records: list[_LibUVCControlRecord] = []
        controls = int(camera_terminal.bmControls)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_CT_AE_MODE_CONTROL,
        ):
            exposure_mode = self._typed_request(
                "uvc_get_ae_mode",
                self._handle,
                ctypes.c_uint8,
                _LIBUVC_GET_CUR,
            )
            if exposure_mode is not None:
                locked = exposure_mode == 1
                records.append(
                    _LibUVCControlRecord(
                        control_id="exposure_mode",
                        label="Exposure Mode",
                        kind="enum",
                        unit_id=int(camera_terminal.bTerminalID),
                        selector=_LIBUVC_CT_AE_MODE_CONTROL,
                        getter_name="uvc_get_ae_mode",
                        setter_name="uvc_set_ae_mode",
                        value=(
                            "manual"
                            if exposure_mode == 1
                            else (
                                "auto"
                                if exposure_mode == 2
                                else (
                                    "shutter_priority"
                                    if exposure_mode == 4
                                    else (
                                        "aperture_priority"
                                        if exposure_mode == 8
                                        else str(exposure_mode)
                                    )
                                )
                            )
                        ),
                        choices=(
                            CameraControlChoice(
                                value="manual", label="Manual"
                            ),
                            CameraControlChoice(value="auto", label="Auto"),
                            CameraControlChoice(
                                value="shutter_priority",
                                label="Shutter Priority",
                            ),
                            CameraControlChoice(
                                value="aperture_priority",
                                label="Aperture Priority",
                            ),
                        ),
                        menu_values=(1, 2, 4, 8),
                        details="UVC auto-exposure mode selector.",
                    )
                )
                records.append(
                    _LibUVCControlRecord(
                        control_id="exposure_locked",
                        label="Exposure Locked",
                        kind="boolean",
                        unit_id=int(camera_terminal.bTerminalID),
                        selector=_LIBUVC_CT_AE_MODE_CONTROL,
                        getter_name="uvc_get_ae_mode",
                        setter_name="uvc_set_ae_mode",
                        value=locked,
                        details="Convenience toggle for manual exposure.",
                    )
                )

        if _libuvc_control_supported(
            controls,
            _LIBUVC_CT_AE_PRIORITY_CONTROL,
        ):
            record = self._boolean_record(
                control_id="exposure_priority",
                label="Exposure Priority",
                getter_name="uvc_get_ae_priority",
                setter_name="uvc_set_ae_priority",
                unit_id=int(camera_terminal.bTerminalID),
                selector=_LIBUVC_CT_AE_PRIORITY_CONTROL,
                details="UVC auto-exposure priority selector.",
            )
            if record is not None:
                records.append(record)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_CT_EXPOSURE_TIME_ABSOLUTE_CONTROL,
        ):
            record = self._numeric_record(
                control_id="manual_exposure_time",
                label="Manual Exposure Time",
                getter_name="uvc_get_exposure_abs",
                setter_name="uvc_set_exposure_abs",
                unit_id=int(camera_terminal.bTerminalID),
                selector=_LIBUVC_CT_EXPOSURE_TIME_ABSOLUTE_CONTROL,
                value_type=ctypes.c_uint32,
                unit="s",
                scale=0.0001,
                details="UVC exposure time in seconds.",
            )
            if record is not None:
                records.append(record)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_CT_FOCUS_ABSOLUTE_CONTROL,
        ):
            record = self._numeric_record(
                control_id="focus_distance",
                label="Focus Distance",
                getter_name="uvc_get_focus_abs",
                setter_name="uvc_set_focus_abs",
                unit_id=int(camera_terminal.bTerminalID),
                selector=_LIBUVC_CT_FOCUS_ABSOLUTE_CONTROL,
                value_type=ctypes.c_uint16,
                details="UVC focus absolute position.",
            )
            if record is not None:
                records.append(record)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_CT_FOCUS_AUTO_CONTROL,
        ):
            record = self._boolean_record(
                control_id="focus_auto",
                label="Focus Automatic",
                getter_name="uvc_get_focus_auto",
                setter_name="uvc_set_focus_auto",
                unit_id=int(camera_terminal.bTerminalID),
                selector=_LIBUVC_CT_FOCUS_AUTO_CONTROL,
                details="UVC auto-focus selector.",
            )
            if record is not None:
                records.append(record)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_CT_ZOOM_ABSOLUTE_CONTROL,
        ):
            record = self._numeric_record(
                control_id="zoom_factor",
                label="Zoom Factor",
                getter_name="uvc_get_zoom_abs",
                setter_name="uvc_set_zoom_abs",
                unit_id=int(camera_terminal.bTerminalID),
                selector=_LIBUVC_CT_ZOOM_ABSOLUTE_CONTROL,
                value_type=ctypes.c_uint16,
                unit="x",
                details="UVC zoom absolute position.",
            )
            if record is not None:
                records.append(record)

        return tuple(records)

    def _processing_unit_controls(
        self,
        processing_unit: _LibUVCProcessingUnit,
    ) -> tuple[_LibUVCControlRecord, ...]:
        """Return the processing-unit controls exposed by libuvc."""

        records: list[_LibUVCControlRecord] = []
        controls = int(processing_unit.bmControls)
        unit_id = int(processing_unit.bUnitID)

        numeric_specs = (
            (
                _LIBUVC_PU_BACKLIGHT_COMPENSATION_CONTROL,
                "backlight_compensation",
                "Backlight Compensation",
                "uvc_get_backlight_compensation",
                "uvc_set_backlight_compensation",
                ctypes.c_uint16,
                "EV",
                1.0,
                "UVC backlight compensation.",
            ),
            (
                _LIBUVC_PU_BRIGHTNESS_CONTROL,
                "brightness",
                "Brightness",
                "uvc_get_brightness",
                "uvc_set_brightness",
                ctypes.c_int16,
                "",
                1.0,
                "UVC brightness.",
            ),
            (
                _LIBUVC_PU_CONTRAST_CONTROL,
                "contrast",
                "Contrast",
                "uvc_get_contrast",
                "uvc_set_contrast",
                ctypes.c_uint16,
                "",
                1.0,
                "UVC contrast.",
            ),
            (
                _LIBUVC_PU_GAIN_CONTROL,
                "gain",
                "Gain",
                "uvc_get_gain",
                "uvc_set_gain",
                ctypes.c_uint16,
                "",
                1.0,
                "UVC gain.",
            ),
            (
                _LIBUVC_PU_HUE_CONTROL,
                "hue",
                "Hue",
                "uvc_get_hue",
                "uvc_set_hue",
                ctypes.c_int16,
                "",
                1.0,
                "UVC hue.",
            ),
            (
                _LIBUVC_PU_SATURATION_CONTROL,
                "saturation",
                "Saturation",
                "uvc_get_saturation",
                "uvc_set_saturation",
                ctypes.c_uint16,
                "",
                1.0,
                "UVC saturation.",
            ),
            (
                _LIBUVC_PU_SHARPNESS_CONTROL,
                "sharpness",
                "Sharpness",
                "uvc_get_sharpness",
                "uvc_set_sharpness",
                ctypes.c_uint16,
                "",
                1.0,
                "UVC sharpness.",
            ),
            (
                _LIBUVC_PU_GAMMA_CONTROL,
                "gamma",
                "Gamma",
                "uvc_get_gamma",
                "uvc_set_gamma",
                ctypes.c_uint16,
                "",
                1.0,
                "UVC gamma.",
            ),
            (
                _LIBUVC_PU_WHITE_BALANCE_TEMPERATURE_CONTROL,
                "white_balance_temperature",
                "White Balance Temperature",
                "uvc_get_white_balance_temperature",
                "uvc_set_white_balance_temperature",
                ctypes.c_uint16,
                "K",
                1.0,
                "UVC white-balance color temperature.",
            ),
        )
        for (
            selector,
            control_id,
            label,
            getter_name,
            setter_name,
            value_type,
            unit,
            scale,
            details,
        ) in numeric_specs:
            if not _libuvc_control_supported(controls, selector):
                continue
            record = self._numeric_record(
                control_id=control_id,
                label=label,
                getter_name=getter_name,
                setter_name=setter_name,
                unit_id=unit_id,
                selector=selector,
                value_type=value_type,
                unit=unit,
                scale=scale,
                signed=value_type in {ctypes.c_int16},
                details=details,
            )
            if record is not None:
                records.append(record)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_PU_WHITE_BALANCE_TEMPERATURE_AUTO_CONTROL,
        ):
            record = self._boolean_record(
                control_id="white_balance_automatic",
                label="White Balance Automatic",
                getter_name="uvc_get_white_balance_temperature_auto",
                setter_name="uvc_set_white_balance_temperature_auto",
                unit_id=unit_id,
                selector=_LIBUVC_PU_WHITE_BALANCE_TEMPERATURE_AUTO_CONTROL,
                details="UVC white-balance auto selector.",
            )
            if record is not None:
                records.append(record)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_PU_HUE_AUTO_CONTROL,
        ):
            record = self._boolean_record(
                control_id="hue_auto",
                label="Hue Automatic",
                getter_name="uvc_get_hue_auto",
                setter_name="uvc_set_hue_auto",
                unit_id=unit_id,
                selector=_LIBUVC_PU_HUE_AUTO_CONTROL,
                details="UVC hue-auto selector.",
            )
            if record is not None:
                records.append(record)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_PU_CONTRAST_AUTO_CONTROL,
        ):
            record = self._boolean_record(
                control_id="contrast_auto",
                label="Contrast Automatic",
                getter_name="uvc_get_contrast_auto",
                setter_name="uvc_set_contrast_auto",
                unit_id=unit_id,
                selector=_LIBUVC_PU_CONTRAST_AUTO_CONTROL,
                details="UVC contrast-auto selector.",
            )
            if record is not None:
                records.append(record)

        if _libuvc_control_supported(
            controls,
            _LIBUVC_PU_POWER_LINE_FREQUENCY_CONTROL,
        ):
            record = self._power_line_frequency_record(
                unit_id,
                _LIBUVC_PU_POWER_LINE_FREQUENCY_CONTROL,
            )
            if record is not None:
                records.append(record)

        return tuple(records)

    def _extension_unit_controls(
        self,
        extension_unit: _LibUVCExtensionUnit,
    ) -> tuple[_LibUVCControlRecord, ...]:
        """Return vendor-specific extension-unit controls when possible."""

        records: list[_LibUVCControlRecord] = []
        unit_id = int(extension_unit.bUnitID)
        controls = int(extension_unit.bmControls)
        for selector in range(1, 65):
            if not _libuvc_control_supported(controls, selector):
                continue
            current = self._raw_request(
                self._handle,
                unit_id,
                selector,
                _LIBUVC_GET_CUR,
                4,
            )
            if current is None:
                continue
            current_value = int.from_bytes(current, "little", signed=False)
            record = _LibUVCControlRecord(
                control_id=(f"extension_unit_{unit_id}_control_{selector}"),
                label=(f"Extension Unit {unit_id} Control {selector}"),
                kind="numeric",
                unit_id=unit_id,
                selector=selector,
                getter_name="uvc_get_ctrl",
                setter_name="uvc_set_ctrl",
                value=current_value,
                min_value=0.0,
                max_value=float((1 << (len(current) * 8)) - 1),
                step=1.0,
                details=(
                    f"Vendor-specific UVC control {selector} on "
                    f"extension unit {unit_id}."
                ),
                size=len(current),
            )
            records.append(record)
        return tuple(records)

    def list_controls(
        self,
        descriptor: CameraDescriptor,
    ) -> tuple[CameraControl, ...]:
        """Return the current libuvc control surface."""

        if not self.available:
            return ()
        device = self._device_for_descriptor(descriptor)
        if device is None:
            return ()
        handle = self._open_device_handle(device)
        if handle is None:
            return ()
        self._handle = handle
        try:
            records: list[_LibUVCControlRecord] = []
            camera_terminal = getattr(
                self._lib,
                "uvc_get_camera_terminal",
                lambda _handle: None,
            )(handle)
            if camera_terminal:
                records.extend(
                    self._camera_terminal_controls(camera_terminal.contents)
                )
            processing_unit = getattr(
                self._lib,
                "uvc_get_processing_units",
                lambda _handle: None,
            )(handle)
            while processing_unit:
                records.extend(
                    self._processing_unit_controls(processing_unit.contents)
                )
                processing_unit = processing_unit.contents.next
            extension_unit = getattr(
                self._lib,
                "uvc_get_extension_units",
                lambda _handle: None,
            )(handle)
            while extension_unit:
                records.extend(
                    self._extension_unit_controls(extension_unit.contents)
                )
                extension_unit = extension_unit.contents.next
            controls: list[CameraControl] = []
            for record in records:
                controls.append(
                    CameraControl(
                        control_id=record.control_id,
                        label=record.label,
                        kind=record.kind,
                        value=record.value,
                        choices=record.choices,
                        min_value=record.min_value,
                        max_value=record.max_value,
                        step=record.step,
                        read_only=record.read_only,
                        enabled=record.enabled,
                        unit=record.unit,
                        details=record.details,
                        action_label=record.action_label,
                    )
                )
            return tuple(controls)
        finally:
            self._handle = None
            self._close_device_handle(handle)

    def _record_for_control_id(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> _LibUVCControlRecord | None:
        """Return one libuvc record for a control ID."""

        for control in self.list_controls(descriptor):
            if control.control_id == control_id:
                return _LibUVCControlRecord(
                    control_id=control.control_id,
                    label=control.label,
                    kind=control.kind,
                    unit_id=0,
                    selector=0,
                    getter_name="",
                    setter_name="",
                    value=control.value,
                    choices=control.choices,
                    menu_values=(),
                    min_value=control.min_value,
                    max_value=control.max_value,
                    step=control.step,
                    read_only=control.read_only,
                    enabled=control.enabled,
                    unit=control.unit,
                    details=control.details,
                    action_label=control.action_label,
                )
        return None

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one libuvc control value."""

        if not self.available:
            raise CameraControlApplyError(
                "The native UVC bridge is unavailable."
            )
        device = self._device_for_descriptor(descriptor)
        if device is None:
            raise CameraControlApplyError(
                "The selected camera could not be found for control updates."
            )
        handle = self._open_device_handle(device)
        if handle is None:
            raise CameraControlApplyError(
                "The native UVC bridge could not open the selected camera."
            )
        self._handle = handle
        try:
            if control_id == "exposure_locked":
                locked = bool(value)
                ae_mode = 1 if locked else 2
                setter = getattr(self._lib, "uvc_set_ae_mode", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support exposure mode changes."
                    )
                result_code = setter(handle, ae_mode)
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "restore_auto_exposure":
                setter = getattr(self._lib, "uvc_set_ae_mode", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support exposure mode changes."
                    )
                result_code = setter(handle, 2)
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "exposure_priority":
                setter = getattr(self._lib, "uvc_set_ae_priority", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support exposure priority."
                    )
                result_code = setter(handle, 1 if bool(value) else 0)
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "manual_exposure_time":
                exposure_time = _safe_float(value)
                if exposure_time is None:
                    raise CameraControlApplyError(
                        "Manual exposure time must be numeric."
                    )
                setter = getattr(self._lib, "uvc_set_exposure_abs", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support manual exposure."
                    )
                raw_value = int(round(exposure_time / 0.0001))
                result_code = setter(handle, raw_value)
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "focus_auto":
                setter = getattr(self._lib, "uvc_set_focus_auto", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support auto focus."
                    )
                result_code = setter(handle, 1 if bool(value) else 0)
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "focus_distance":
                focus_distance = _safe_float(value)
                if focus_distance is None:
                    raise CameraControlApplyError(
                        "Focus distance must be numeric."
                    )
                setter = getattr(self._lib, "uvc_set_focus_abs", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support manual focus."
                    )
                result_code = setter(handle, int(round(focus_distance)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "zoom_factor":
                zoom_value = _safe_float(value)
                if zoom_value is None:
                    raise CameraControlApplyError("Zoom must be numeric.")
                setter = getattr(self._lib, "uvc_set_zoom_abs", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support zoom."
                    )
                result_code = setter(handle, int(round(zoom_value)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "backlight_compensation":
                setter = getattr(
                    self._lib,
                    "uvc_set_backlight_compensation",
                    None,
                )
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support backlight compensation."
                    )
                compensation = _safe_float(value)
                if compensation is None:
                    raise CameraControlApplyError(
                        "Backlight compensation must be numeric."
                    )
                result_code = setter(handle, int(round(compensation)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "brightness":
                setter = getattr(self._lib, "uvc_set_brightness", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support brightness."
                    )
                brightness = _safe_float(value)
                if brightness is None:
                    raise CameraControlApplyError(
                        "Brightness must be numeric."
                    )
                result_code = setter(handle, int(round(brightness)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "contrast":
                setter = getattr(self._lib, "uvc_set_contrast", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support contrast."
                    )
                contrast = _safe_float(value)
                if contrast is None:
                    raise CameraControlApplyError("Contrast must be numeric.")
                result_code = setter(handle, int(round(contrast)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "contrast_auto":
                setter = getattr(self._lib, "uvc_set_contrast_auto", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support automatic contrast."
                    )
                result_code = setter(handle, 1 if bool(value) else 0)
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "gain":
                setter = getattr(self._lib, "uvc_set_gain", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support gain."
                    )
                gain = _safe_float(value)
                if gain is None:
                    raise CameraControlApplyError("Gain must be numeric.")
                result_code = setter(handle, int(round(gain)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "power_line_frequency":
                setter = getattr(
                    self._lib,
                    "uvc_set_power_line_frequency",
                    None,
                )
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support power-line frequency."
                    )
                token = (_settings_text(value) or "").lower()
                power_map = {
                    "disabled": 0,
                    "50": 1,
                    "60": 2,
                    "auto": 3,
                }
                if token not in power_map:
                    raise CameraControlApplyError(
                        f"Unsupported power-line frequency `{token}`."
                    )
                result_code = setter(handle, power_map[token])
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "hue":
                setter = getattr(self._lib, "uvc_set_hue", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support hue."
                    )
                hue = _safe_float(value)
                if hue is None:
                    raise CameraControlApplyError("Hue must be numeric.")
                result_code = setter(handle, int(round(hue)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "hue_auto":
                setter = getattr(self._lib, "uvc_set_hue_auto", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support automatic hue."
                    )
                result_code = setter(handle, 1 if bool(value) else 0)
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "saturation":
                setter = getattr(self._lib, "uvc_set_saturation", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support saturation."
                    )
                saturation = _safe_float(value)
                if saturation is None:
                    raise CameraControlApplyError(
                        "Saturation must be numeric."
                    )
                result_code = setter(handle, int(round(saturation)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "sharpness":
                setter = getattr(self._lib, "uvc_set_sharpness", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support sharpness."
                    )
                sharpness = _safe_float(value)
                if sharpness is None:
                    raise CameraControlApplyError("Sharpness must be numeric.")
                result_code = setter(handle, int(round(sharpness)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "gamma":
                setter = getattr(self._lib, "uvc_set_gamma", None)
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support gamma."
                    )
                gamma = _safe_float(value)
                if gamma is None:
                    raise CameraControlApplyError("Gamma must be numeric.")
                result_code = setter(handle, int(round(gamma)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "white_balance_temperature":
                setter = getattr(
                    self._lib,
                    "uvc_set_white_balance_temperature",
                    None,
                )
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support "
                        "white balance temperature."
                    )
                temperature = _safe_float(value)
                if temperature is None:
                    raise CameraControlApplyError(
                        "White balance temperature must be numeric."
                    )
                result_code = setter(handle, int(round(temperature)))
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id == "white_balance_automatic":
                setter = getattr(
                    self._lib,
                    "uvc_set_white_balance_temperature_auto",
                    None,
                )
                if setter is None:
                    raise CameraControlApplyError(
                        "The camera does not support automatic white balance."
                    )
                result_code = setter(handle, 1 if bool(value) else 0)
                if result_code != 0:
                    raise CameraControlApplyError(
                        self._uvc_error_text(result_code)
                    )
                return
            if control_id.startswith("extension_unit_"):
                record = self._record_for_control_id(descriptor, control_id)
                if record is None:
                    raise CameraControlApplyError(
                        f"Unsupported camera control `{control_id}`."
                    )
                raw_value = _safe_float(value)
                if raw_value is None:
                    raise CameraControlApplyError(
                        f"The control `{control_id}` must be numeric."
                    )
                size = max(record.size, 1)
                payload = int(round(raw_value)).to_bytes(
                    size,
                    byteorder="little",
                    signed=record.signed,
                )
                self._raw_write(
                    handle, record.unit_id, record.selector, payload
                )
                return
            raise CameraControlApplyError(
                f"Unsupported camera control `{control_id}`."
            )
        finally:
            self._handle = None
            self._close_device_handle(handle)

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one libuvc action control."""

        if control_id != "restore_auto_exposure":
            raise CameraControlApplyError(
                f"Unsupported action control `{control_id}`."
            )
        self.set_control_value(descriptor, control_id, True)


def _build_control_backend(
    qt_multimedia: Any | None,
    qt_device_resolver: Callable[[CameraDescriptor], Any | None] | None,
    v4l2_device_resolver: Callable[[CameraDescriptor], str | None] | None,
    *,
    preferred_source_format_getter: (
        Callable[[CameraDescriptor], str | None] | None
    ) = None,
    preferred_source_format_setter: (
        Callable[[CameraDescriptor, str | None], None] | None
    ) = None,
) -> CameraControlBackend:
    """Return the single active control backend for one runtime."""

    control_backends: list[CameraControlBackend] = []
    if sys.platform.startswith("linux") and v4l2_device_resolver is not None:
        control_backends.append(
            LinuxV4L2CameraControlBackend(
                v4l2_device_resolver,
            )
        )
    elif sys.platform == "win32":
        if qt_multimedia is not None and qt_device_resolver is not None:
            control_backends.append(
                QtCameraControlBackend(
                    qt_multimedia,
                    qt_device_resolver,
                    preferred_source_format_getter,
                    preferred_source_format_setter,
                )
            )
    elif sys.platform == "darwin":
        libuvc_backend = LibUVCControlBackend()
        if libuvc_backend.available:
            control_backends.append(libuvc_backend)
        control_backends.append(AvFoundationCameraControlBackend())
    if not control_backends:
        return NullCameraControlBackend()
    if len(control_backends) == 1:
        return control_backends[0]
    return _SelectedCameraControlBackend(*control_backends)


_QT_EXPOSURE_MODE_SPECS = (
    ("continuous_auto", "ExposureAuto", "Continuous Auto"),
    ("locked", "ExposureManual", "Locked"),
)
_QT_FLASH_MODE_SPECS = (
    ("off", "FlashOff", "Off"),
    ("on", "FlashOn", "On"),
    ("auto", "FlashAuto", "Auto"),
)
_QT_TORCH_MODE_SPECS = (
    ("off", "TorchOff", "Off"),
    ("on", "TorchOn", "On"),
    ("auto", "TorchAuto", "Auto"),
)
_AVFOUNDATION_EXPOSURE_MODE_SPECS = (
    (0, "locked", "Locked"),
    (1, "auto", "Auto"),
    (2, "continuous_auto", "Continuous Auto"),
    (3, "custom", "Custom"),
)
_AVFOUNDATION_FOCUS_MODE_SPECS = (
    (0, "locked", "Locked"),
    (1, "auto", "Auto"),
    (2, "continuous_auto", "Continuous Auto"),
)
_AVFOUNDATION_WHITE_BALANCE_MODE_SPECS = (
    (0, "locked", "Locked"),
    (1, "auto", "Auto"),
    (2, "continuous_auto", "Continuous Auto"),
)
_AVFOUNDATION_FLASH_MODE_SPECS = (
    (0, "off", "Off"),
    (1, "on", "On"),
    (2, "auto", "Auto"),
)
_AVFOUNDATION_TORCH_MODE_SPECS = (
    (0, "off", "Off"),
    (1, "on", "On"),
    (2, "auto", "Auto"),
)


def _avfoundation_choice_list(
    device: Any,
    support_method_name: str,
    specs: tuple[tuple[int, str, str], ...],
) -> tuple[CameraControlChoice, ...]:
    """Return the supported AVFoundation choices for one control."""

    support_method = getattr(device, support_method_name, None)
    if support_method is None:
        return ()
    choices: list[CameraControlChoice] = []
    for raw_value, token, label in specs:
        try:
            if not support_method(raw_value):
                continue
        except (AttributeError, RuntimeError, TypeError, ValueError):
            continue
        choices.append(CameraControlChoice(value=token, label=label))
    return tuple(choices)


def _avfoundation_choice_token(
    current_value: object,
    specs: tuple[tuple[int, str, str], ...],
) -> str | None:
    """Return the stable token for one AVFoundation enum value."""

    for raw_value, token, _label in specs:
        if current_value == raw_value:
            return token
    return None


def _avfoundation_choice_value(
    token: str,
    specs: tuple[tuple[int, str, str], ...],
) -> int | None:
    """Return one AVFoundation enum value for a stable token."""

    for raw_value, spec_token, _label in specs:
        if spec_token == token:
            return raw_value
    return None


def _avfoundation_cmtime_seconds(value: object) -> float | None:
    """Return the seconds stored in one AVFoundation CMTime structure."""

    try:
        raw_value = float(getattr(value, "field_0"))
        timescale = float(getattr(value, "field_1"))
    except (AttributeError, TypeError, ValueError):
        return None
    if timescale <= 0:
        return None
    return raw_value / timescale


def _avfoundation_cmtime_from_seconds(
    seconds: float,
    *,
    reference: object | None = None,
) -> object:
    """Return one AVFoundation CMTime structure from a seconds value."""

    reference_type = type(reference) if reference is not None else None
    if reference_type is None:
        raise CameraControlApplyError(
            "Could not build a camera timing value for this device."
        )
    reference_timescale = 0
    if reference is not None:
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            reference_timescale = int(getattr(reference, "field_1", 0))
    timescale = reference_timescale if reference_timescale > 0 else 1_000_000
    raw_value = int(round(seconds * timescale))
    return reference_type(raw_value, timescale, 0, 0)


class QtCameraControlBackend:
    """Expose Qt Multimedia camera controls on every supported platform."""

    def __init__(
        self,
        qt_multimedia: Any,
        device_resolver: Callable[[CameraDescriptor], Any | None],
        preferred_source_format_getter: (
            Callable[[CameraDescriptor], str | None] | None
        ) = None,
        preferred_source_format_setter: (
            Callable[[CameraDescriptor, str | None], None] | None
        ) = None,
    ) -> None:
        """Store the Qt modules and descriptor resolver used for controls."""

        self._qt_multimedia = qt_multimedia
        self._device_resolver = device_resolver
        self._preferred_source_format_getter = preferred_source_format_getter
        self._preferred_source_format_setter = preferred_source_format_setter

    def _camera_for_descriptor(
        self, descriptor: CameraDescriptor
    ) -> Any | None:
        """Return the Qt camera object for one shared descriptor."""

        camera_device = self._device_resolver(descriptor)
        if camera_device is None:
            return None
        camera_class = getattr(self._qt_multimedia, "QCamera", None)
        if camera_class is None:
            return None
        camera = camera_class(camera_device)
        camera_format = self._camera_format_for_descriptor(
            descriptor,
            camera_device,
        )
        if camera_format is not None:
            with contextlib.suppress(
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ):
                camera.setCameraFormat(camera_format)
        return camera

    def _preferred_source_format(
        self, descriptor: CameraDescriptor
    ) -> str | None:
        """Return the stored Qt source-format token for one descriptor."""

        if self._preferred_source_format_getter is None:
            return None
        return self._preferred_source_format_getter(descriptor)

    def _set_preferred_source_format(
        self,
        descriptor: CameraDescriptor,
        token: str | None,
    ) -> None:
        """Store one preferred Qt source-format token for a descriptor."""

        if self._preferred_source_format_setter is None:
            return
        self._preferred_source_format_setter(descriptor, token)

    def _camera_format_for_descriptor(
        self,
        descriptor: CameraDescriptor,
        camera_device: object,
    ) -> object | None:
        """Return the preferred Qt camera format for one descriptor."""

        token = self._preferred_source_format(descriptor)
        camera_format = _qcamera_camera_format_for_token(
            camera_device,
            token,
        )
        if camera_format is not None:
            return camera_format
        return _qcamera_camera_format_for_token(camera_device, None)

    def _source_format_choices(
        self, camera_device: object
    ) -> tuple[CameraControlChoice, ...]:
        """Return the available Qt source-format choices for one device."""

        return _qcamera_camera_format_choices(camera_device)

    def _exposure_mode_choices(
        self, camera: Any
    ) -> tuple[CameraControlChoice, ...]:
        """Return the writable exposure-mode choices for one Qt camera."""

        camera_class = self._qt_multimedia.QCamera
        return _qcamera_choice_list(
            camera,
            camera_class.ExposureMode,
            "isExposureModeSupported",
            _QT_EXPOSURE_MODE_SPECS,
        )

    def _flash_mode_choices(
        self, camera: Any
    ) -> tuple[CameraControlChoice, ...]:
        """Return the writable flash-mode choices for one Qt camera."""

        camera_class = self._qt_multimedia.QCamera
        return _qcamera_choice_list(
            camera,
            camera_class.FlashMode,
            "isFlashModeSupported",
            _QT_FLASH_MODE_SPECS,
        )

    def _torch_mode_choices(
        self, camera: Any
    ) -> tuple[CameraControlChoice, ...]:
        """Return the writable torch-mode choices for one Qt camera."""

        camera_class = self._qt_multimedia.QCamera
        return _qcamera_choice_list(
            camera,
            camera_class.TorchMode,
            "isTorchModeSupported",
            _QT_TORCH_MODE_SPECS,
        )

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the current Qt Multimedia control surface."""

        camera_device = self._device_resolver(descriptor)
        if camera_device is None:
            return ()
        camera = self._camera_for_descriptor(descriptor)
        if camera is None:
            return ()
        camera_class = self._qt_multimedia.QCamera
        features = getattr(camera, "supportedFeatures", lambda: 0)()
        controls: list[CameraControl] = []

        source_format_choices = self._source_format_choices(camera_device)
        if source_format_choices:
            current_source_format = self._preferred_source_format(descriptor)
            if current_source_format not in {
                choice.value for choice in source_format_choices
            }:
                current_source_format = source_format_choices[0].value
            controls.append(
                CameraControl(
                    control_id="source_format",
                    label="Resolution",
                    kind="enum",
                    value=current_source_format,
                    choices=source_format_choices,
                    read_only=len(source_format_choices) < 2,
                    enabled=len(source_format_choices) > 1,
                    details="Supported camera source resolutions.",
                )
            )

        exposure_choices = self._exposure_mode_choices(camera)
        if exposure_choices:
            current_exposure_mode = (
                _qcamera_choice_token(
                    getattr(camera, "exposureMode", lambda: None)(),
                    camera_class.ExposureMode,
                    _QT_EXPOSURE_MODE_SPECS,
                )
                or exposure_choices[0].value
            )
            controls.append(
                CameraControl(
                    control_id="exposure_mode",
                    label="Exposure Mode",
                    kind="enum",
                    value=current_exposure_mode,
                    choices=exposure_choices,
                    details=(
                        "Qt Multimedia exposure mode for the active " "camera."
                    ),
                )
            )
            if len(exposure_choices) > 1:
                controls.append(
                    CameraControl(
                        control_id="exposure_locked",
                        label="Exposure Locked",
                        kind="boolean",
                        value=current_exposure_mode == "locked",
                        details=(
                            "Convenience toggle between continuous auto "
                            "and manual exposure."
                        ),
                    )
                )

        if _qcamera_feature_supported(
            camera,
            features,
            camera_class.Feature.ExposureCompensation,
            "exposureCompensation",
            "setExposureCompensation",
        ):
            exposure_compensation = _safe_float(
                getattr(camera, "exposureCompensation", lambda: 0.0)()
            )
            if exposure_compensation is None:
                exposure_compensation = 0.0
            exposure_compensation = max(-4.0, min(4.0, exposure_compensation))
            controls.append(
                CameraControl(
                    control_id="backlight_compensation",
                    label="Backlight Compensation",
                    kind="numeric",
                    value=exposure_compensation,
                    min_value=-4.0,
                    max_value=4.0,
                    step=0.1,
                    details="Qt Multimedia exposure compensation in EV.",
                )
            )

        manual_exposure_supported = _qcamera_feature_supported(
            camera,
            features,
            camera_class.Feature.ManualExposureTime,
            "minimumExposureTime",
            "maximumExposureTime",
            "manualExposureTime",
            "setManualExposureTime",
            "setExposureMode",
        )
        if manual_exposure_supported:
            minimum_exposure = _safe_float(
                getattr(camera, "minimumExposureTime", lambda: 0.0)()
            )
            maximum_exposure = _safe_float(
                getattr(camera, "maximumExposureTime", lambda: 0.0)()
            )
            current_exposure_time = _safe_float(
                getattr(camera, "manualExposureTime", lambda: 0.0)()
            )
            if (
                minimum_exposure is not None
                and maximum_exposure is not None
                and minimum_exposure > 0
                and maximum_exposure > minimum_exposure
            ):
                if current_exposure_time is None:
                    current_exposure_time = minimum_exposure
                current_exposure_time = max(
                    minimum_exposure,
                    min(maximum_exposure, current_exposure_time),
                )
                controls.append(
                    CameraControl(
                        control_id="manual_exposure_time",
                        label="Manual Exposure Time",
                        kind="numeric",
                        value=current_exposure_time,
                        min_value=minimum_exposure,
                        max_value=maximum_exposure,
                        step=_numeric_step(minimum_exposure, maximum_exposure),
                        details="Manual exposure time in seconds.",
                    )
                )

        focus_auto_supported = getattr(camera, "isFocusModeSupported", None)
        if focus_auto_supported is not None:
            try:
                focus_auto = bool(
                    camera.isFocusModeSupported(
                        camera_class.FocusMode.FocusModeAuto
                    )
                )
                focus_manual = bool(
                    camera.isFocusModeSupported(
                        camera_class.FocusMode.FocusModeManual
                    )
                )
            except (AttributeError, RuntimeError, TypeError, ValueError):
                focus_auto = False
                focus_manual = False
            if focus_auto or focus_manual:
                current_focus_mode = getattr(
                    camera, "focusMode", lambda: None
                )()
                controls.append(
                    CameraControl(
                        control_id="focus_auto",
                        label="Focus Automatic",
                        kind="boolean",
                        value=current_focus_mode
                        == camera_class.FocusMode.FocusModeAuto,
                        read_only=not (focus_auto and focus_manual),
                        enabled=focus_auto and focus_manual,
                        details="Auto or manual focus selection.",
                    )
                )

        if _qcamera_feature_supported(
            camera,
            features,
            camera_class.Feature.FocusDistance,
            "focusDistance",
            "setFocusDistance",
        ):
            current_focus_distance = _safe_float(
                getattr(camera, "focusDistance", lambda: 1.0)()
            )
            if current_focus_distance is None:
                current_focus_distance = 1.0
            current_focus_distance = max(
                0.0,
                min(1.0, current_focus_distance),
            )
            controls.append(
                CameraControl(
                    control_id="focus_distance",
                    label="Focus Distance",
                    kind="numeric",
                    value=current_focus_distance,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01,
                    details="Manual focus distance between near and far.",
                )
            )

        white_balance_auto_supported = getattr(
            camera, "isWhiteBalanceModeSupported", None
        )
        if white_balance_auto_supported is not None:
            try:
                white_balance_auto = bool(
                    camera.isWhiteBalanceModeSupported(
                        camera_class.WhiteBalanceMode.WhiteBalanceAuto
                    )
                )
                white_balance_manual = bool(
                    camera.isWhiteBalanceModeSupported(
                        camera_class.WhiteBalanceMode.WhiteBalanceManual
                    )
                )
            except (AttributeError, RuntimeError, TypeError, ValueError):
                white_balance_auto = False
                white_balance_manual = False
            if white_balance_auto or white_balance_manual:
                current_white_balance_mode = getattr(
                    camera, "whiteBalanceMode", lambda: None
                )()
                controls.append(
                    CameraControl(
                        control_id="white_balance_automatic",
                        label="White Balance Automatic",
                        kind="boolean",
                        value=current_white_balance_mode
                        == camera_class.WhiteBalanceMode.WhiteBalanceAuto,
                        read_only=not (
                            white_balance_auto and white_balance_manual
                        ),
                        enabled=white_balance_auto and white_balance_manual,
                        details="Auto or manual white balance selection.",
                    )
                )

        if _qcamera_feature_supported(
            camera,
            features,
            camera_class.Feature.ColorTemperature,
            "colorTemperature",
            "setColorTemperature",
        ):
            current_color_temperature = _safe_float(
                getattr(camera, "colorTemperature", lambda: 2800)()
            )
            if current_color_temperature is None:
                current_color_temperature = 2800.0
            current_color_temperature = max(
                2000.0,
                min(10000.0, current_color_temperature),
            )
            controls.append(
                CameraControl(
                    control_id="white_balance_temperature",
                    label="White Balance Temperature",
                    kind="numeric",
                    value=current_color_temperature,
                    min_value=2000.0,
                    max_value=10000.0,
                    step=100.0,
                    details=(
                        "Manual white balance color temperature in Kelvin."
                    ),
                )
            )

        flash_choices = self._flash_mode_choices(camera)
        if flash_choices:
            current_flash_mode = (
                _qcamera_choice_token(
                    getattr(camera, "flashMode", lambda: None)(),
                    camera_class.FlashMode,
                    _QT_FLASH_MODE_SPECS,
                )
                or flash_choices[0].value
            )
            controls.append(
                CameraControl(
                    control_id="flash_mode",
                    label="Flash Mode",
                    kind="enum",
                    value=current_flash_mode,
                    choices=flash_choices,
                    read_only=len(flash_choices) < 2,
                    enabled=len(flash_choices) > 1,
                    details="Flash mode for still capture when available.",
                )
            )

        torch_choices = self._torch_mode_choices(camera)
        if torch_choices:
            current_torch_mode = (
                _qcamera_choice_token(
                    getattr(camera, "torchMode", lambda: None)(),
                    camera_class.TorchMode,
                    _QT_TORCH_MODE_SPECS,
                )
                or torch_choices[0].value
            )
            controls.append(
                CameraControl(
                    control_id="torch_mode",
                    label="Torch Mode",
                    kind="enum",
                    value=current_torch_mode,
                    choices=torch_choices,
                    read_only=len(torch_choices) < 2,
                    enabled=len(torch_choices) > 1,
                    details="Torch or illumination mode for live lighting.",
                )
            )

        zoom_minimum = (
            _safe_float(getattr(camera, "minimumZoomFactor", lambda: 1.0)())
            or 1.0
        )
        zoom_maximum = (
            _safe_float(getattr(camera, "maximumZoomFactor", lambda: 1.0)())
            or 1.0
        )
        zoom_value = _safe_float(getattr(camera, "zoomFactor", lambda: 1.0)())
        if zoom_value is None:
            zoom_value = zoom_minimum
        zoom_value = max(zoom_minimum, min(zoom_maximum, zoom_value))
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
                details="Qt Multimedia video zoom factor.",
            )
        )

        camera_format = getattr(camera, "cameraFormat", None)
        if callable(camera_format):
            camera_format = camera_format()
        if camera_format is not None:
            controls.append(
                CameraControl(
                    control_id="active_format",
                    label="Active Format",
                    kind="read_only",
                    value=_qcamera_camera_format_text(camera_format),
                    details="Current Qt Multimedia camera format.",
                )
            )

        if exposure_choices and manual_exposure_supported:
            controls.append(
                CameraControl(
                    control_id="restore_auto_exposure",
                    label="Restore Auto Exposure",
                    kind="action",
                    value=None,
                    action_label="Restore",
                    details="Return the camera to automatic exposure control.",
                )
            )

        return tuple(controls)

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one Qt Multimedia control value."""

        camera = self._camera_for_descriptor(descriptor)
        if camera is None:
            raise CameraControlApplyError(
                "The selected camera could not be found for control updates."
            )
        camera_class = self._qt_multimedia.QCamera
        features = getattr(camera, "supportedFeatures", lambda: 0)()

        if control_id == "exposure_mode":
            mode_value = _qcamera_choice_value(
                str(value),
                camera_class.ExposureMode,
                _QT_EXPOSURE_MODE_SPECS,
            )
            if mode_value is None:
                raise CameraControlApplyError(
                    "Unsupported exposure mode selection."
                )
            try:
                camera.setExposureMode(mode_value)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "source_format":
            camera_device = self._device_resolver(descriptor)
            if camera_device is None:
                raise CameraControlApplyError(
                    "The selected camera could not be found for control "
                    "updates."
                )
            token = str(value).strip()
            if not token:
                raise CameraControlApplyError(
                    "Resolution must be set to one supported format."
                )
            source_format = _qcamera_camera_format_for_token(
                camera_device,
                token,
            )
            if source_format is None:
                raise CameraControlApplyError(
                    "Unsupported resolution selection."
                )
            self._set_preferred_source_format(descriptor, token)
            return

        if control_id == "exposure_locked":
            mode_value = (
                camera_class.ExposureMode.ExposureManual
                if bool(value)
                else camera_class.ExposureMode.ExposureAuto
            )
            try:
                camera.setExposureMode(mode_value)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "backlight_compensation":
            if not _qcamera_feature_supported(
                camera,
                features,
                camera_class.Feature.ExposureCompensation,
                "exposureCompensation",
                "setExposureCompensation",
            ):
                raise CameraControlApplyError(
                    "Backlight compensation is unavailable for this camera."
                )
            compensation = _safe_float(value)
            if compensation is None:
                raise CameraControlApplyError(
                    "Backlight compensation must be numeric."
                )
            try:
                camera.setExposureCompensation(compensation)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "manual_exposure_time":
            exposure_time = _safe_float(value)
            if exposure_time is None:
                raise CameraControlApplyError(
                    "Manual exposure time must be numeric."
                )
            if not _qcamera_feature_supported(
                camera,
                features,
                camera_class.Feature.ManualExposureTime,
                "minimumExposureTime",
                "maximumExposureTime",
                "manualExposureTime",
                "setManualExposureTime",
                "setExposureMode",
            ):
                raise CameraControlApplyError(
                    "Manual exposure time is unavailable for this camera."
                )
            try:
                camera.setExposureMode(
                    camera_class.ExposureMode.ExposureManual
                )
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            try:
                camera.setManualExposureTime(exposure_time)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "focus_auto":
            focus_mode = (
                camera_class.FocusMode.FocusModeAuto
                if bool(value)
                else camera_class.FocusMode.FocusModeManual
            )
            try:
                camera.setFocusMode(focus_mode)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "focus_distance":
            if not _qcamera_feature_supported(
                camera,
                features,
                camera_class.Feature.FocusDistance,
                "focusDistance",
                "setFocusDistance",
            ):
                raise CameraControlApplyError(
                    "Focus distance is unavailable for this camera."
                )
            focus_distance = _safe_float(value)
            if focus_distance is None:
                raise CameraControlApplyError(
                    "Focus distance must be numeric."
                )
            try:
                camera.setFocusMode(camera_class.FocusMode.FocusModeManual)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            try:
                camera.setFocusDistance(max(0.0, min(1.0, focus_distance)))
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "white_balance_automatic":
            white_balance_mode = (
                camera_class.WhiteBalanceMode.WhiteBalanceAuto
                if bool(value)
                else camera_class.WhiteBalanceMode.WhiteBalanceManual
            )
            try:
                camera.setWhiteBalanceMode(white_balance_mode)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "white_balance_temperature":
            if not _qcamera_feature_supported(
                camera,
                features,
                camera_class.Feature.ColorTemperature,
                "colorTemperature",
                "setColorTemperature",
            ):
                raise CameraControlApplyError(
                    "White balance temperature is unavailable for this "
                    "camera."
                )
            color_temperature = _safe_float(value)
            if color_temperature is None:
                raise CameraControlApplyError(
                    "White balance temperature must be numeric."
                )
            try:
                camera.setColorTemperature(int(round(color_temperature)))
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "flash_mode":
            mode_value = _qcamera_choice_value(
                str(value),
                camera_class.FlashMode,
                _QT_FLASH_MODE_SPECS,
            )
            if mode_value is None:
                raise CameraControlApplyError(
                    "Unsupported flash mode selection."
                )
            try:
                camera.setFlashMode(mode_value)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "torch_mode":
            mode_value = _qcamera_choice_value(
                str(value),
                camera_class.TorchMode,
                _QT_TORCH_MODE_SPECS,
            )
            if mode_value is None:
                raise CameraControlApplyError(
                    "Unsupported torch mode selection."
                )
            try:
                camera.setTorchMode(mode_value)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "zoom_factor":
            zoom_value = _safe_float(value)
            if zoom_value is None:
                raise CameraControlApplyError("Zoom must be numeric.")
            minimum = (
                _safe_float(
                    getattr(camera, "minimumZoomFactor", lambda: 1.0)()
                )
                or 1.0
            )
            maximum = (
                _safe_float(
                    getattr(camera, "maximumZoomFactor", lambda: 1.0)()
                )
                or 1.0
            )
            if maximum <= minimum + 0.001:
                raise CameraControlApplyError("Zoom is fixed on this camera.")
            try:
                camera.setZoomFactor(max(minimum, min(maximum, zoom_value)))
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            return

        if control_id == "restore_auto_exposure":
            try:
                camera.setExposureMode(camera_class.ExposureMode.ExposureAuto)
            except (
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CameraControlApplyError(str(exc)) from exc
            with contextlib.suppress(
                AttributeError, RuntimeError, TypeError, ValueError
            ):
                camera.setAutoExposureTime()
            with contextlib.suppress(
                AttributeError, RuntimeError, TypeError, ValueError
            ):
                camera.setAutoIsoSensitivity()
            return

        raise CameraControlApplyError(
            f"Unsupported camera control `{control_id}`."
        )

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one Qt Multimedia action control."""

        if control_id != "restore_auto_exposure":
            raise CameraControlApplyError(
                f"Unsupported action control `{control_id}`."
            )
        self.set_control_value(
            descriptor,
            "restore_auto_exposure",
            True,
        )


class AvFoundationCameraControlBackend:
    """Expose macOS AVFoundation camera controls when the bridge is present."""

    def __init__(self) -> None:
        """Load the bridge modules used to inspect and configure controls."""

        self._capture_device_class, self._video_media_type = (
            _load_avfoundation_modules()
        )
        self._pending_configuration_completions: dict[object, Any] = {}
        self._pending_configuration_completion_lock = threading.Lock()

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

    def _mode_choices(
        self,
        device: Any,
        support_method_name: str,
        specs: tuple[tuple[int, str, str], ...],
    ) -> tuple[CameraControlChoice, ...]:
        """Return the supported mode choices for one AVFoundation device."""

        return _avfoundation_choice_list(device, support_method_name, specs)

    def _mode_token(
        self,
        current_value: object,
        specs: tuple[tuple[int, str, str], ...],
    ) -> str | None:
        """Return the stable token for one AVFoundation enum value."""

        return _avfoundation_choice_token(current_value, specs)

    def _mode_value(
        self,
        token: str,
        specs: tuple[tuple[int, str, str], ...],
    ) -> int | None:
        """Return one AVFoundation enum value for a stable token."""

        return _avfoundation_choice_value(token, specs)

    def _backlight_compensation_range(
        self,
        device: Any,
        active_format: Any,
    ) -> tuple[float, float] | None:
        """Return the supported exposure-bias range when available."""

        support_method = getattr(device, "isExposureModeSupported_", None)
        if support_method is None:
            return None
        try:
            if not (bool(support_method(0)) or bool(support_method(2))):
                return None
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None

        if active_format is not None and hasattr(
            active_format,
            "systemRecommendedExposureBiasRange",
        ):
            bias_range = _call_or_value(
                getattr(
                    active_format,
                    "systemRecommendedExposureBiasRange",
                    None,
                )
            )
            if bias_range is None:
                return None
            min_bias = _safe_float(
                _call_or_value(getattr(bias_range, "minExposureBias", None))
            )
            max_bias = _safe_float(
                _call_or_value(getattr(bias_range, "maxExposureBias", None))
            )
            if min_bias is None or max_bias is None or max_bias <= min_bias:
                return None
            return min_bias, max_bias

        if not (
            hasattr(device, "minExposureTargetBias")
            and hasattr(device, "maxExposureTargetBias")
            and hasattr(device, "exposureTargetBias")
            and hasattr(device, "setExposureTargetBias_completionHandler_")
        ):
            return None

        min_bias = _safe_float(_call_or_value(device.minExposureTargetBias))
        max_bias = _safe_float(_call_or_value(device.maxExposureTargetBias))
        if min_bias is None:
            min_bias = -4.0
        if max_bias is None or max_bias <= min_bias:
            max_bias = 4.0
        return min_bias, max_bias

    def _white_balance_locked_supported(self, device: Any) -> bool:
        """Return whether the device can lock white balance manually."""

        locking_supported = getattr(
            device,
            "isLockingWhiteBalanceWithCustomDeviceGainsSupported",
            None,
        )
        if locking_supported is None:
            return False
        try:
            return bool(_call_or_value(locking_supported))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False

    def _white_balance_temperature_supported(self, device: Any) -> bool:
        """Return whether locked white balance temperature is safe."""

        setter = getattr(
            device,
            "setWhiteBalanceModeLockedWithDeviceWhiteBalanceTemperatureAnd"
            "TintValues_completionHandler_",
            None,
        )
        if setter is None:
            return False
        return (
            getattr(
                device,
                "temperatureAndTintValuesForDeviceWhiteBalanceGains_",
                None,
            )
            is not None
            and getattr(device, "deviceWhiteBalanceGains", None) is not None
        )

    def _cmtime_seconds(self, value: object) -> float | None:
        """Return the seconds represented by one AVFoundation CMTime."""

        return _avfoundation_cmtime_seconds(value)

    def _cmtime_from_seconds(
        self,
        seconds: float,
        *,
        reference: object | None = None,
    ) -> object:
        """Return one AVFoundation CMTime built from a seconds value."""

        return _avfoundation_cmtime_from_seconds(
            seconds,
            reference=reference,
        )

    def _white_balance_temperature_tint_values(
        self,
        device: Any,
    ) -> tuple[object | None, float | None, float]:
        """Return the current white-balance temperature, tint, and struct."""

        conversion = getattr(
            device,
            "temperatureAndTintValuesForDeviceWhiteBalanceGains_",
            None,
        )
        gains_method = getattr(device, "deviceWhiteBalanceGains", None)
        if conversion is None or gains_method is None:
            return None, None, 0.0
        try:
            gains = gains_method()
            values = conversion(gains)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None, None, 0.0
        temperature = _safe_float(getattr(values, "field_0", None))
        tint = _safe_float(getattr(values, "field_1", None)) or 0.0
        return values, temperature, tint

    def _custom_exposure_supported(self, device: Any) -> bool:
        """Return whether the device can safely use custom exposure."""

        setter = getattr(
            device,
            "setExposureModeCustomWithDuration_ISO_completionHandler_",
            None,
        )
        if setter is None:
            return False
        active_format = _call_or_value(getattr(device, "activeFormat", None))
        if active_format is None:
            return False
        if not hasattr(device, "ISO"):
            return False
        if not hasattr(active_format, "minExposureDuration"):
            return False
        if not hasattr(active_format, "maxExposureDuration"):
            return False
        return True

    def _smooth_auto_focus_supported(self, device: Any) -> bool:
        """Return whether the device can safely use smooth autofocus."""

        support_method = getattr(device, "isSmoothAutoFocusSupported", None)
        if support_method is None:
            return False
        try:
            return bool(support_method())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False

    def _video_hdr_supported(self, active_format: Any) -> bool:
        """Return whether the active format can safely expose video HDR."""

        if active_format is None or not hasattr(
            active_format, "isVideoHDRSupported"
        ):
            return False
        try:
            return bool(active_format.isVideoHDRSupported())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False

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

        exposure_choices = self._mode_choices(
            device,
            "isExposureModeSupported_",
            _AVFOUNDATION_EXPOSURE_MODE_SPECS,
        )
        if exposure_choices:
            current_exposure_mode = self._mode_token(
                _call_or_value(getattr(device, "exposureMode", None)),
                _AVFOUNDATION_EXPOSURE_MODE_SPECS,
            )
            if current_exposure_mode is None:
                current_exposure_mode = exposure_choices[0].value
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
            supports_lock_toggle = _choice_for_value(
                exposure_choices,
                "locked",
            ) is not None and (
                _choice_for_value(
                    exposure_choices,
                    "continuous_auto",
                )
                is not None
                or _choice_for_value(
                    exposure_choices,
                    "auto",
                )
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

        active_format = _call_or_value(getattr(device, "activeFormat", None))
        custom_exposure_supported = self._custom_exposure_supported(device)
        exposure_duration_supported = (
            custom_exposure_supported
            and active_format is not None
            and hasattr(active_format, "minExposureDuration")
            and hasattr(active_format, "maxExposureDuration")
            and hasattr(
                device,
                "setExposureModeCustomWithDuration_ISO_completionHandler_",
            )
            and hasattr(device, "ISO")
        )
        if exposure_duration_supported:
            min_exposure = self._cmtime_seconds(
                getattr(active_format, "minExposureDuration")
            )
            max_exposure = self._cmtime_seconds(
                getattr(active_format, "maxExposureDuration")
            )
            if min_exposure is None or min_exposure <= 0:
                min_exposure = 0.0001
            if max_exposure is None or max_exposure <= min_exposure:
                max_exposure = max(1.0, min_exposure * 1000)
            current_exposure = self._cmtime_seconds(
                _call_or_value(getattr(device, "exposureDuration", None))
            )
            if current_exposure is None or current_exposure <= 0:
                current_exposure = min_exposure
            controls.append(
                CameraControl(
                    control_id="manual_exposure_time",
                    label="Manual Exposure Time",
                    kind="numeric",
                    value=current_exposure,
                    min_value=min_exposure,
                    max_value=max_exposure,
                    step=_numeric_step(min_exposure, max_exposure),
                    unit="s",
                    details="Manual exposure time in seconds.",
                )
            )

        backlight_compensation_range = self._backlight_compensation_range(
            device,
            active_format,
        )
        if backlight_compensation_range is not None:
            min_bias, max_bias = backlight_compensation_range
            current_bias = _safe_float(
                _call_or_value(getattr(device, "exposureTargetBias", None))
            )
            if current_bias is None:
                current_bias = 0.0
            current_bias = max(min_bias, min(max_bias, current_bias))
            controls.append(
                CameraControl(
                    control_id="backlight_compensation",
                    label="Backlight Compensation",
                    kind="numeric",
                    value=current_bias,
                    min_value=min_bias,
                    max_value=max_bias,
                    step=_numeric_step(min_bias, max_bias),
                    unit="EV",
                    details="AVFoundation exposure bias in EV.",
                )
            )

        focus_choices = self._mode_choices(
            device,
            "isFocusModeSupported_",
            _AVFOUNDATION_FOCUS_MODE_SPECS,
        )
        if focus_choices:
            current_focus_mode = self._mode_token(
                _call_or_value(getattr(device, "focusMode", None)),
                _AVFOUNDATION_FOCUS_MODE_SPECS,
            )
            if current_focus_mode is None:
                current_focus_mode = focus_choices[0].value
            supports_focus_toggle = (
                _choice_for_value(focus_choices, "locked") is not None
                and _choice_for_value(focus_choices, "auto") is not None
            ) or (
                _choice_for_value(focus_choices, "locked") is not None
                and _choice_for_value(
                    focus_choices,
                    "continuous_auto",
                )
                is not None
            )
            if supports_focus_toggle:
                controls.append(
                    CameraControl(
                        control_id="focus_auto",
                        label="Focus Automatic",
                        kind="boolean",
                        value=current_focus_mode != "locked",
                        read_only=False,
                        enabled=True,
                        details="Auto or manual focus selection.",
                    )
                )

        if hasattr(device, "lensPosition") and hasattr(
            device, "setFocusModeLockedWithLensPosition_completionHandler_"
        ):
            current_focus_distance = _safe_float(
                _call_or_value(device.lensPosition)
            )
            if current_focus_distance is None:
                current_focus_distance = 0.0
            current_focus_distance = max(0.0, min(1.0, current_focus_distance))
            controls.append(
                CameraControl(
                    control_id="focus_distance",
                    label="Focus Distance",
                    kind="numeric",
                    value=current_focus_distance,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01,
                    details="Manual focus lens position between near and far.",
                )
            )

        white_balance_choices = self._mode_choices(
            device,
            "isWhiteBalanceModeSupported_",
            _AVFOUNDATION_WHITE_BALANCE_MODE_SPECS,
        )
        current_white_balance_mode = self._mode_token(
            _call_or_value(getattr(device, "whiteBalanceMode", None)),
            _AVFOUNDATION_WHITE_BALANCE_MODE_SPECS,
        )
        if current_white_balance_mode is None:
            current_white_balance_mode = (
                white_balance_choices[0].value
                if white_balance_choices
                else "auto"
            )
        locked_supported = self._white_balance_locked_supported(device)
        white_balance_writable = locked_supported or (
            _choice_for_value(white_balance_choices, "locked") is not None
        )
        if white_balance_writable:
            controls.append(
                CameraControl(
                    control_id="white_balance_automatic",
                    label="White Balance Automatic",
                    kind="boolean",
                    value=current_white_balance_mode != "locked",
                    read_only=False,
                    enabled=True,
                    details="Auto or manual white balance selection.",
                )
            )

        temperature_tint_values, current_temperature, current_tint = (
            self._white_balance_temperature_tint_values(device)
        )
        supports_temperature_tint_update = (
            white_balance_writable
            and temperature_tint_values is not None
            and self._white_balance_temperature_supported(device)
        )
        if supports_temperature_tint_update:
            if current_temperature is None or current_temperature <= 0:
                current_temperature = 2800.0
            controls.append(
                CameraControl(
                    control_id="white_balance_temperature",
                    label="White Balance Temperature",
                    kind="numeric",
                    value=current_temperature,
                    min_value=2000.0,
                    max_value=10000.0,
                    step=100.0,
                    unit="K",
                    details=(
                        "Manual white balance color temperature in Kelvin."
                    ),
                )
            )

        flash_choices = self._mode_choices(
            device,
            "isFlashModeSupported_",
            _AVFOUNDATION_FLASH_MODE_SPECS,
        )
        if flash_choices:
            current_flash_mode = self._mode_token(
                _call_or_value(getattr(device, "flashMode", None)),
                _AVFOUNDATION_FLASH_MODE_SPECS,
            )
            if current_flash_mode is None:
                current_flash_mode = flash_choices[0].value
            controls.append(
                CameraControl(
                    control_id="flash_mode",
                    label="Flash Mode",
                    kind="enum",
                    value=current_flash_mode,
                    choices=flash_choices,
                    read_only=len(flash_choices) < 2,
                    enabled=len(flash_choices) > 1,
                    details="Flash mode for still capture when available.",
                )
            )

        torch_choices = self._mode_choices(
            device,
            "isTorchModeSupported_",
            _AVFOUNDATION_TORCH_MODE_SPECS,
        )
        if torch_choices:
            current_torch_mode = self._mode_token(
                _call_or_value(getattr(device, "torchMode", None)),
                _AVFOUNDATION_TORCH_MODE_SPECS,
            )
            if current_torch_mode is None:
                current_torch_mode = torch_choices[0].value
            controls.append(
                CameraControl(
                    control_id="torch_mode",
                    label="Torch Mode",
                    kind="enum",
                    value=current_torch_mode,
                    choices=torch_choices,
                    read_only=len(torch_choices) < 2,
                    enabled=len(torch_choices) > 1,
                    details="Torch or illumination mode for live lighting.",
                )
            )

        if (
            self._video_hdr_supported(active_format)
            and hasattr(device, "automaticallyAdjustsVideoHDREnabled")
            and hasattr(device, "setAutomaticallyAdjustsVideoHDREnabled_")
        ):
            controls.append(
                CameraControl(
                    control_id="video_hdr_automatic",
                    label="Automatic Video HDR",
                    kind="boolean",
                    value=bool(
                        _call_or_value(
                            device.automaticallyAdjustsVideoHDREnabled
                        )
                    ),
                    details="Automatic HDR adjustments when supported.",
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

        if _choice_for_value(exposure_choices, "auto") is not None or (
            _choice_for_value(exposure_choices, "continuous_auto") is not None
        ):
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

    def _configuration_completion(
        self,
        device: Any,
    ) -> tuple[Any, Callable[[], None], threading.Event]:
        """Return one retained release hook and a no-op wait flag."""

        token = object()
        lock_released = False
        completed = threading.Event()
        completed.set()

        def release() -> None:
            """Release the device lock and drop the retained block."""

            nonlocal lock_released
            if lock_released:
                return
            lock_released = True
            with self._pending_configuration_completion_lock:
                self._pending_configuration_completions.pop(token, None)
            with contextlib.suppress(Exception):
                device.unlockForConfiguration()

        with self._pending_configuration_completion_lock:
            self._pending_configuration_completions[token] = None
        return None, release, completed

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
        custom_exposure_supported = self._custom_exposure_supported(device)
        if (
            control_id
            in {
                "manual_exposure_time",
            }
            and not custom_exposure_supported
        ):
            raise CameraControlApplyError(
                "The camera does not support custom exposure."
            )
        self._lock_device(device)
        active_format = _call_or_value(getattr(device, "activeFormat", None))

        (
            temperature_tint_values,
            current_temperature,
            current_tint,
        ) = self._white_balance_temperature_tint_values(device)
        defer_unlock = False
        try:
            if control_id == "exposure_mode":
                mode_value = self._mode_value(
                    str(value),
                    _AVFOUNDATION_EXPOSURE_MODE_SPECS,
                )
                if mode_value is None:
                    raise CameraControlApplyError(
                        "Unsupported exposure mode selection."
                    )
                if not device.isExposureModeSupported_(mode_value):
                    raise CameraControlApplyError(
                        "The camera does not support that exposure mode."
                    )
                if mode_value == 3:
                    if not custom_exposure_supported:
                        raise CameraControlApplyError(
                            "The camera does not support custom exposure."
                        )
                    duration_reference = _call_or_value(
                        getattr(device, "exposureDuration", None)
                    )
                    if self._cmtime_seconds(duration_reference) is None:
                        duration_reference = getattr(
                            active_format,
                            "minExposureDuration",
                            None,
                        )
                    if duration_reference is None:
                        raise CameraControlApplyError(
                            "Custom exposure timing is unavailable."
                        )
                    duration_seconds = self._cmtime_seconds(duration_reference)
                    if duration_seconds is None or duration_seconds <= 0:
                        duration_seconds = 0.001
                    iso_value = _safe_float(
                        _call_or_value(getattr(device, "ISO", None))
                    )
                    if iso_value is None or iso_value <= 0:
                        iso_value = _safe_float(
                            getattr(active_format, "minISO", None)
                        )
                    if iso_value is None or iso_value <= 0:
                        iso_value = 100.0
                    completion, release_completion, completion_done = (
                        self._configuration_completion(device)
                    )
                    set_custom_exposure = getattr(
                        device,
                        "setExposureModeCustomWithDuration_ISO_"
                        "completionHandler_",
                    )
                    try:
                        set_custom_exposure(
                            self._cmtime_from_seconds(
                                duration_seconds,
                                reference=duration_reference,
                            ),
                            iso_value,
                            completion,
                        )
                    except (
                        AttributeError,
                        RuntimeError,
                        TypeError,
                        ValueError,
                    ):
                        release_completion()
                        raise
                    completion_done.wait()
                    defer_unlock = True
                    release_completion()
                    return
                device.setExposureMode_(mode_value)
                return
            if control_id == "exposure_locked":
                mode_value = 0 if bool(value) else 2
                if not device.isExposureModeSupported_(mode_value):
                    if not bool(value) and device.isExposureModeSupported_(1):
                        mode_value = 1
                    else:
                        raise CameraControlApplyError(
                            "The camera cannot switch exposure lock state."
                        )
                device.setExposureMode_(mode_value)
                return
            if control_id == "manual_exposure_time":
                exposure_time = _safe_float(value)
                if exposure_time is None:
                    raise CameraControlApplyError(
                        "Manual exposure time must be numeric."
                    )
                min_exposure = self._cmtime_seconds(
                    getattr(active_format, "minExposureDuration", None)
                )
                max_exposure = self._cmtime_seconds(
                    getattr(active_format, "maxExposureDuration", None)
                )
                if min_exposure is None or min_exposure <= 0:
                    min_exposure = 0.0001
                if max_exposure is None or max_exposure <= min_exposure:
                    max_exposure = max(1.0, min_exposure * 1000)
                bounded_time = max(
                    min_exposure,
                    min(max_exposure, exposure_time),
                )
                duration_reference = _call_or_value(
                    getattr(device, "exposureDuration", None)
                )
                if self._cmtime_seconds(duration_reference) is None:
                    duration_reference = getattr(
                        active_format,
                        "minExposureDuration",
                        None,
                    )
                if duration_reference is None:
                    raise CameraControlApplyError(
                        "Manual exposure timing is unavailable."
                    )
                iso_value = _safe_float(
                    _call_or_value(getattr(device, "ISO", None))
                )
                if iso_value is None or iso_value <= 0:
                    iso_value = _safe_float(
                        getattr(active_format, "minISO", None)
                    )
                if iso_value is None or iso_value <= 0:
                    iso_value = 100.0
                completion, release_completion, completion_done = (
                    self._configuration_completion(device)
                )
                set_custom_exposure = getattr(
                    device,
                    "setExposureModeCustomWithDuration_ISO_"
                    "completionHandler_",
                )
                try:
                    set_custom_exposure(
                        self._cmtime_from_seconds(
                            bounded_time,
                            reference=duration_reference,
                        ),
                        iso_value,
                        completion,
                    )
                except (
                    AttributeError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                ):
                    release_completion()
                    raise
                completion_done.wait()
                defer_unlock = True
                release_completion()
                return
            if control_id == "backlight_compensation":
                backlight_compensation_range = (
                    self._backlight_compensation_range(
                        device,
                        active_format,
                    )
                )
                if backlight_compensation_range is None:
                    raise CameraControlApplyError(
                        "The camera does not support backlight "
                        "compensation."
                    )
                min_bias, max_bias = backlight_compensation_range
                compensation = _safe_float(value)
                if compensation is None:
                    raise CameraControlApplyError(
                        "Backlight compensation must be numeric."
                    )
                compensation = max(min_bias, min(max_bias, compensation))
                completion, release_completion, completion_done = (
                    self._configuration_completion(device)
                )
                try:
                    device.setExposureTargetBias_completionHandler_(
                        compensation,
                        completion,
                    )
                except (
                    AttributeError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                ) as exc:
                    release_completion()
                    raise CameraControlApplyError(
                        "The camera does not support backlight "
                        "compensation."
                    ) from exc
                completion_done.wait()
                defer_unlock = True
                release_completion()
                return
            if control_id == "focus_auto":
                locked_supported = bool(device.isFocusModeSupported_(0))
                auto_mode = 2 if device.isFocusModeSupported_(2) else 1
                if bool(value):
                    if auto_mode == 2 and not device.isFocusModeSupported_(2):
                        raise CameraControlApplyError(
                            "The camera cannot switch focus to auto."
                        )
                    if auto_mode == 1 and not device.isFocusModeSupported_(1):
                        raise CameraControlApplyError(
                            "The camera cannot switch focus to auto."
                        )
                    device.setFocusMode_(auto_mode)
                    return
                if not locked_supported:
                    raise CameraControlApplyError(
                        "The camera cannot lock focus manually."
                    )
                device.setFocusMode_(0)
                return
            if control_id == "focus_distance":
                focus_distance = _safe_float(value)
                if focus_distance is None:
                    raise CameraControlApplyError(
                        "Focus distance must be numeric."
                    )
                if not device.isFocusModeSupported_(0):
                    raise CameraControlApplyError(
                        "The camera cannot lock focus manually."
                    )
                bounded_value = max(0.0, min(1.0, focus_distance))
                completion, release_completion, completion_done = (
                    self._configuration_completion(device)
                )
                set_focus_mode_locked = getattr(
                    device,
                    "setFocusModeLockedWithLensPosition_completionHandler_",
                )
                try:
                    set_focus_mode_locked(
                        bounded_value,
                        completion,
                    )
                except (
                    AttributeError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                ):
                    release_completion()
                    raise
                completion_done.wait()
                defer_unlock = True
                release_completion()
                return
            if control_id == "white_balance_automatic":
                auto_mode = 2 if device.isWhiteBalanceModeSupported_(2) else 1
                if bool(value):
                    if (
                        auto_mode == 2
                        and not device.isWhiteBalanceModeSupported_(2)
                    ):
                        raise CameraControlApplyError(
                            "The camera cannot switch white balance to auto."
                        )
                    if (
                        auto_mode == 1
                        and not device.isWhiteBalanceModeSupported_(1)
                    ):
                        raise CameraControlApplyError(
                            "The camera cannot switch white balance to auto."
                        )
                    device.setWhiteBalanceMode_(auto_mode)
                    return
                if getattr(device, "setWhiteBalanceMode_", None) is None:
                    raise CameraControlApplyError(
                        "The camera cannot lock white balance manually."
                    )
                device.setWhiteBalanceMode_(0)
                return
            if control_id == "white_balance_temperature":
                white_balance_locked = self._white_balance_locked_supported(
                    device
                )
                if not white_balance_locked:
                    support_method = getattr(
                        device, "isWhiteBalanceModeSupported_", None
                    )
                    if support_method is not None:
                        try:
                            white_balance_locked = bool(support_method(0))
                        except (
                            AttributeError,
                            RuntimeError,
                            TypeError,
                            ValueError,
                        ):
                            white_balance_locked = False
                if not white_balance_locked:
                    raise CameraControlApplyError(
                        "The camera does not support white balance "
                        "temperature control."
                    )
                if not self._white_balance_temperature_supported(device):
                    raise CameraControlApplyError(
                        "The camera does not support white balance "
                        "temperature control."
                    )
                temperature = _safe_float(value)
                if temperature is None:
                    raise CameraControlApplyError(
                        "White balance temperature must be numeric."
                    )
                if temperature_tint_values is None:
                    (
                        temperature_tint_values,
                        current_temperature,
                        current_tint,
                    ) = self._white_balance_temperature_tint_values(device)
                if temperature_tint_values is None:
                    raise CameraControlApplyError(
                        "White balance temperature is unavailable."
                    )
                bounded_temperature = max(2000.0, min(10000.0, temperature))
                tint = current_tint if current_tint is not None else 0.0
                temperature_tint = type(temperature_tint_values)(
                    bounded_temperature,
                    tint,
                )
                completion, release_completion, completion_done = (
                    self._configuration_completion(device)
                )
                set_white_balance_temperature = getattr(
                    device,
                    "setWhiteBalanceModeLockedWithDeviceWhiteBalance"
                    "TemperatureAndTintValues_"
                    "completionHandler_",
                )
                try:
                    set_white_balance_temperature(
                        temperature_tint,
                        completion,
                    )
                except (
                    AttributeError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                ):
                    release_completion()
                    raise
                completion_done.wait()
                defer_unlock = True
                release_completion()
                return
            if control_id == "flash_mode":
                mode_value = self._mode_value(
                    str(value),
                    _AVFOUNDATION_FLASH_MODE_SPECS,
                )
                if mode_value is None:
                    raise CameraControlApplyError(
                        "Unsupported flash mode selection."
                    )
                if not device.isFlashModeSupported_(mode_value):
                    raise CameraControlApplyError(
                        "The camera does not support that flash mode."
                    )
                device.setFlashMode_(mode_value)
                return
            if control_id == "torch_mode":
                mode_value = self._mode_value(
                    str(value),
                    _AVFOUNDATION_TORCH_MODE_SPECS,
                )
                if mode_value is None:
                    raise CameraControlApplyError(
                        "Unsupported torch mode selection."
                    )
                if not device.isTorchModeSupported_(mode_value):
                    raise CameraControlApplyError(
                        "The camera does not support that torch mode."
                    )
                device.setTorchMode_(mode_value)
                return
            if control_id == "video_hdr_automatic":
                if not self._video_hdr_supported(active_format):
                    raise CameraControlApplyError(
                        "The camera does not support video HDR."
                    )
                device.setAutomaticallyAdjustsVideoHDREnabled_(bool(value))
                return
            if control_id == "restore_auto_exposure":
                auto_mode = 2 if device.isExposureModeSupported_(2) else 1
                if not device.isExposureModeSupported_(auto_mode):
                    raise CameraControlApplyError(
                        "The camera cannot restore automatic exposure."
                    )
                device.setExposureMode_(auto_mode)
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
            if not defer_unlock:
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
            "restore_auto_exposure",
            True,
        )


class QtCameraSession:
    """Capture preview frames from one Qt Multimedia camera session."""

    def __init__(
        self,
        descriptor: CameraDescriptor,
        camera_device: Any,
        *,
        camera_format: Any | None = None,
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
        if camera_format is not None:
            with contextlib.suppress(
                AttributeError,
                RuntimeError,
                TypeError,
                ValueError,
            ):
                self._camera.setCameraFormat(camera_format)
        self._preview_capture_session = qt_multimedia.QMediaCaptureSession()
        self._recording_capture_session = qt_multimedia.QMediaCaptureSession()
        self._video_sink = qt_multimedia.QVideoSink()
        self._video_frame_input = qt_multimedia.QVideoFrameInput()
        self._media_recorder = qt_multimedia.QMediaRecorder()
        self._preview_capture_session.setCamera(self._camera)
        self._preview_capture_session.setVideoSink(self._video_sink)
        self._recording_capture_session.setVideoFrameInput(
            self._video_frame_input
        )
        self._recording_capture_session.setRecorder(self._media_recorder)
        self._latest_frame: PreviewFrame | None = None
        self._failure_reason: str | None = None
        self._recording_error: str | None = None
        self._recording_crop_plan: RecordingCropPlan | None = None
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
        if self._recording_crop_plan is not None:
            recording_image = _crop_recording_qimage(
                image,
                crop_plan=self._recording_crop_plan,
            )
            video_frame = self._qt_multimedia.QVideoFrame(recording_image)
            self._video_frame_input.sendVideoFrame(video_frame)
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

    def start_recording(
        self,
        output_path: Path,
        *,
        crop_plan: RecordingCropPlan,
    ) -> Path:
        """Start one Qt Multimedia recording to the requested path."""

        if self._closed:
            raise CameraOutputError("The active camera session is closed.")
        if self._recording_crop_plan is not None:
            raise CameraOutputError("Recording is already active.")
        output_path, file_format = _qt_recording_output_path_for_path(
            output_path,
            self._qt_multimedia,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        media_format = self._qt_multimedia.QMediaFormat()
        media_format.setFileFormat(file_format)
        self._media_recorder.setMediaFormat(media_format)
        self._media_recorder.setQuality(
            self._qt_multimedia.QMediaRecorder.Quality.HighQuality
        )
        self._media_recorder.setOutputLocation(
            self._qt_core.QUrl.fromLocalFile(str(output_path))
        )
        self._recording_crop_plan = crop_plan
        self._recording_error = None
        self._recording_duration_milliseconds = 0
        self._recording_output_path = output_path
        self._media_recorder.record()
        return output_path

    def stop_recording(self) -> Path | None:
        """Stop the active Qt Multimedia recording cleanly."""

        self._recording_crop_plan = None
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
        self._recording_crop_plan = None
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

        return not self._closed and self._media_recorder.isAvailable()

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
        self._preferred_source_format_by_descriptor: dict[str, str] = {}
        self._control_backend = _build_control_backend(
            self._qt_multimedia,
            self._camera_device_for_descriptor,
            _v4l2_device_path_for_descriptor,
            preferred_source_format_getter=(
                self._preferred_source_format_for_descriptor
            ),
            preferred_source_format_setter=(
                self._set_preferred_source_format_for_descriptor
            ),
        )

    def _camera_device_for_descriptor(
        self, descriptor: CameraDescriptor
    ) -> Any | None:
        """Return the Qt camera device matching one shared descriptor."""

        return _qt_camera_device_for_descriptor(
            self._qt_multimedia, descriptor
        )

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return the cameras Qt Multimedia can currently enumerate."""

        return _discover_qt_cameras()

    def _preferred_source_format_for_descriptor(
        self, descriptor: CameraDescriptor
    ) -> str | None:
        """Return the stored preferred source-format token for one camera."""

        return self._preferred_source_format_by_descriptor.get(
            descriptor.stable_id
        )

    def _set_preferred_source_format_for_descriptor(
        self,
        descriptor: CameraDescriptor,
        token: str | None,
    ) -> None:
        """Store one preferred source-format token for a camera."""

        if token is None:
            self._preferred_source_format_by_descriptor.pop(
                descriptor.stable_id,
                None,
            )
            return
        self._preferred_source_format_by_descriptor[descriptor.stable_id] = (
            token
        )

    def _camera_format_for_descriptor(
        self,
        descriptor: CameraDescriptor,
    ) -> object | None:
        """Return the preferred Qt camera format for one descriptor."""

        camera_device = self._camera_device_for_descriptor(descriptor)
        if camera_device is None:
            return None
        token = self._preferred_source_format_for_descriptor(descriptor)
        camera_format = _qcamera_camera_format_for_token(camera_device, token)
        if camera_format is not None:
            return camera_format
        return _qcamera_camera_format_for_token(camera_device, None)

    def _source_format_control_for_descriptor(
        self,
        descriptor: CameraDescriptor,
    ) -> CameraControl | None:
        """Return the preview-owned source-format row for one camera."""

        camera_device = self._camera_device_for_descriptor(descriptor)
        if camera_device is None:
            return None
        source_format_choices = _qcamera_camera_format_choices(camera_device)
        if not source_format_choices:
            return None
        current_source_format = self._preferred_source_format_for_descriptor(
            descriptor
        )
        if current_source_format not in {
            choice.value for choice in source_format_choices
        }:
            current_source_format = source_format_choices[0].value
        return CameraControl(
            control_id="source_format",
            label="Resolution",
            kind="enum",
            value=current_source_format,
            choices=source_format_choices,
            read_only=len(source_format_choices) < 2,
            enabled=len(source_format_choices) > 1,
            details="Supported camera source resolutions.",
        )

    def open_session(self, descriptor: CameraDescriptor) -> QtCameraSession:
        """Open one Qt camera session for the provided descriptor."""

        camera_device = self._camera_device_for_descriptor(descriptor)
        if camera_device is None:
            raise CameraOpenError(
                "The selected camera could not be found in the current Qt "
                "device list."
            )
        assert self._qt_gui is not None
        assert self._qt_core is not None
        assert self._qt_multimedia is not None
        return QtCameraSession(
            descriptor=descriptor,
            camera_device=camera_device,
            camera_format=self._camera_format_for_descriptor(descriptor),
            qt_core=self._qt_core,
            qt_gui=self._qt_gui,
            qt_multimedia=self._qt_multimedia,
        )

    def list_controls(
        self, descriptor: CameraDescriptor
    ) -> tuple[CameraControl, ...]:
        """Return the control surface for the selected camera."""

        controls: list[CameraControl] = []
        if not isinstance(self._control_backend, QtCameraControlBackend):
            source_format = self._source_format_control_for_descriptor(
                descriptor
            )
            if source_format is not None:
                controls.append(source_format)
        controls.extend(self._control_backend.list_controls(descriptor))
        return tuple(controls)

    def set_control_value(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
        value: object,
    ) -> None:
        """Apply one control value through the selected control backend."""

        if control_id == "source_format" and not isinstance(
            self._control_backend, QtCameraControlBackend
        ):
            camera_device = self._camera_device_for_descriptor(descriptor)
            if camera_device is None:
                raise CameraControlApplyError(
                    "The selected camera could not be found for control "
                    "updates."
                )
            token = str(value).strip()
            if not token:
                raise CameraControlApplyError(
                    "Resolution must be set to one supported format."
                )
            source_format = _qcamera_camera_format_for_token(
                camera_device,
                token,
            )
            if source_format is None:
                raise CameraControlApplyError(
                    "Resolution must be set to one supported format."
                )
            self._set_preferred_source_format_for_descriptor(descriptor, token)
            return
        self._control_backend.set_control_value(descriptor, control_id, value)

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one action control through the selected backend."""

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
        (
            self._qt_core,
            self._qt_gui,
            self._qt_multimedia,
        ) = _load_qt_camera_modules()
        self._control_backend = _build_control_backend(
            self._qt_multimedia,
            (
                lambda descriptor: (
                    _qt_camera_device_for_descriptor(
                        self._qt_multimedia,
                        descriptor,
                    )
                    if self._qt_multimedia is not None
                    else None
                )
            ),
            lambda descriptor: (
                descriptor.device_selector
                if str(descriptor.device_selector).startswith("/dev/video")
                else _v4l2_device_path_for_descriptor(descriptor)
            ),
        )

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
        """Apply one control value through the selected control backend."""

        self._control_backend.set_control_value(descriptor, control_id, value)

    def trigger_control_action(
        self,
        descriptor: CameraDescriptor,
        control_id: str,
    ) -> None:
        """Trigger one action control through the selected backend."""

        self._control_backend.trigger_control_action(
            descriptor,
            control_id,
        )
