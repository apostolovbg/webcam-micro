"""Foundation constants for the `webcam_micro` prototype package."""

APP_NAME = "webcam-micro"
PACKAGE_NAME = "webcam_micro"
GUI_BASELINE = "PySide6 Qt Widgets"
BACKEND_STRATEGY = (
    "Qt Widgets owns the native desktop shell while Qt Multimedia now owns "
    "camera discovery, capture sessions, and live preview; the repo layer "
    "keeps microscope-specific framing, outputs, defaults, diagnostics, a "
    "rubicon-backed AVFoundation permission bridge on macOS, and one "
    "selected device-control owner per camera, matched by canonical device "
    "identity and limited to feature-backed exposure, focus, white balance, "
    "light, flicker, zoom, and vendor-specific settings, with Linux V4L2 "
    "adding extra device-specific discovery when available."
)
SHELL_TITLE = "webcam-micro workspace"
