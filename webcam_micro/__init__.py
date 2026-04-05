"""Foundation constants for the `webcam_micro` prototype package."""

APP_NAME = "webcam-micro"
PACKAGE_NAME = "webcam_micro"
GUI_BASELINE = "PySide6 Qt Widgets"
BACKEND_STRATEGY = (
    "Qt Widgets owns the native desktop shell while Qt Multimedia now owns "
    "camera discovery, capture sessions, live preview, and the common "
    "control surface; the repo layer keeps microscope-specific framing, "
    "outputs, defaults, diagnostics, a rubicon-backed AVFoundation "
    "permission bridge on macOS, macOS AVFoundation control discovery "
    "on Intel and Apple silicon Macs, and Linux V4L2 control discovery "
    "for extra light, flicker, and vendor-specific settings."
)
SHELL_TITLE = "webcam-micro workspace"
