"""Camera backend contracts for the Stage 1 prototype foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CameraDescriptor:
    """Describe one backend-exposed camera candidate."""

    stable_id: str
    display_name: str
    backend_name: str


class CameraSession(Protocol):
    """Represent one open camera session lifecycle."""

    def close(self) -> None:
        """Release backend resources for the active session."""


class CameraBackend(Protocol):
    """Represent the shared camera-backend contract used by the UI."""

    backend_name: str

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return the cameras the backend can currently expose."""

    def open_session(self, descriptor: CameraDescriptor) -> CameraSession:
        """Open one camera session for the provided descriptor."""


@dataclass(frozen=True)
class BackendPlan:
    """Summarize the chosen Stage 1 backend direction."""

    stage_one_backend: str
    first_device_backend_target: str
    notes: tuple[str, ...]


def build_backend_plan() -> BackendPlan:
    """Return the documented backend baseline for the prototype."""

    return BackendPlan(
        stage_one_backend="NullCameraBackend",
        first_device_backend_target=(
            "OpenCV-backed discovery and preview behind the adapter layer"
        ),
        notes=(
            "Stage 1 keeps device I/O out of the package skeleton.",
            "Stage 2 will replace the null backend with real discovery and "
            "preview wiring.",
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


class NullCameraBackend:
    """Provide the Stage 1 backend placeholder without real device I/O."""

    backend_name = "null"

    def discover_cameras(self) -> tuple[CameraDescriptor, ...]:
        """Return no devices for the placeholder backend."""

        return ()

    def open_session(self, descriptor: CameraDescriptor) -> NullCameraSession:
        """Return a placeholder session for the requested descriptor."""

        return NullCameraSession(descriptor=descriptor)
