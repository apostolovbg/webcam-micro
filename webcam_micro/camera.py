"""Camera discovery and preview backends for the Stage 2 baseline."""

from __future__ import annotations

import contextlib
import glob
import re
import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CameraDescriptor:
    """Describe one backend-exposed camera candidate."""

    stable_id: str
    display_name: str
    backend_name: str
    device_selector: str


class CameraSession(Protocol):
    """Represent one open camera session lifecycle."""

    def close(self) -> None:
        """Release backend resources for the active session."""

    def get_latest_frame(self) -> PreviewFrame | None:
        """Return the newest available preview frame."""

    @property
    def failure_reason(self) -> str | None:
        """Return the most recent recoverable session failure."""


class CameraBackend(Protocol):
    """Represent the shared camera-backend contract used by the UI."""

    backend_name: str

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return the cameras the backend can currently expose."""

    def open_session(self, descriptor: CameraDescriptor) -> CameraSession:
        """Open one camera session for the provided descriptor."""


@dataclass(frozen=True)
class PreviewFrame:
    """Represent one RGB preview frame for the UI."""

    width: int
    height: int
    rgb_bytes: bytes
    frame_number: int


@dataclass(frozen=True)
class BackendPlan:
    """Summarize the chosen Stage 2 backend direction."""

    active_backend: str
    first_device_backend_target: str
    notes: tuple[str, ...]


def build_backend_plan() -> BackendPlan:
    """Return the documented backend baseline for the prototype."""

    return BackendPlan(
        active_backend="FfmpegCameraBackend",
        first_device_backend_target="FFmpeg-backed discovery and live preview",
        notes=(
            "Stage 2 discovers cameras through platform-aware FFmpeg "
            "enumeration.",
            "Preview readers keep only the newest frame to avoid lag from "
            "stale buffered frames.",
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


class NullCameraBackend:
    """Provide a fallback backend when real device I/O is unavailable."""

    backend_name = "null"

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return no devices for the placeholder backend."""

        return ()

    def open_session(self, descriptor: CameraDescriptor) -> NullCameraSession:
        """Return a placeholder session for the requested descriptor."""

        return NullCameraSession(descriptor=descriptor)


class MissingCameraDependencyError(RuntimeError):
    """Raised when the runtime camera backend dependency is unavailable."""


def _load_imageio_ffmpeg():
    """Import the FFmpeg helper lazily so smoke tests stay lightweight."""

    try:
        import imageio_ffmpeg
    except ModuleNotFoundError:
        return None
    return imageio_ffmpeg


def _ffmpeg_executable() -> str:
    """Return the managed FFmpeg binary path."""

    imageio_ffmpeg = _load_imageio_ffmpeg()
    if imageio_ffmpeg is None:
        raise MissingCameraDependencyError(
            "Install the package runtime dependencies before opening a "
            "camera session."
        )
    return imageio_ffmpeg.get_ffmpeg_exe()


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
        descriptors.append(
            CameraDescriptor(
                stable_id=f"ffmpeg:avfoundation:{device_index}",
                display_name=device_name,
                backend_name="ffmpeg",
                device_selector=device_index,
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


class FfmpegCameraBackend:
    """Discover cameras and open low-latency preview sessions with FFmpeg."""

    backend_name = "ffmpeg"
    preview_width = 640
    preview_height = 480

    def __init__(self) -> None:
        """Validate that the runtime camera dependency is available."""

        self._ffmpeg_exe = _ffmpeg_executable()

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
