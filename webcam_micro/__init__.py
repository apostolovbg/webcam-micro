"""Foundation constants for the `webcam_micro` prototype package."""

APP_NAME = "webcam-micro"
PACKAGE_NAME = "webcam_micro"
GUI_BASELINE = "PySide6 Qt Widgets"
BACKEND_STRATEGY = (
    "Qt Widgets owns the native desktop shell while Qt Multimedia now owns "
    "camera discovery, capture sessions, and live preview; the repo layer "
    "keeps microscope-specific framing, outputs, defaults, diagnostics, and "
    "a rubicon-backed AVFoundation control bridge on macOS for real camera "
    "settings."
)
SHELL_TITLE = "webcam-micro workspace"
