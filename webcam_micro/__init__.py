"""Foundation constants for the `webcam_micro` prototype package."""

APP_NAME = "webcam-micro"
PACKAGE_NAME = "webcam_micro"
GUI_BASELINE = "PySide6 Qt Widgets"
BACKEND_STRATEGY = (
    "Qt Widgets owns the native desktop shell while Qt Multimedia owns "
    "camera discovery, preview, and recording; the repo layer keeps "
    "microscope-specific framing, outputs, defaults, diagnostics, a "
    "rubicon-backed AVFoundation permission bridge on macOS, and one "
    "platform-selected device-control owner per camera. Canonical device "
    "identity chooses that owner, preview-owned source-format selection "
    "stays separate, and Linux V4L2 adds extra device-specific discovery "
    "when available."
)
SHELL_TITLE = "webcam-micro workspace"
