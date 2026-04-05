"""Qt Widgets workstation shell assembly for the current PySide6 baseline."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from webcam_micro import APP_NAME, GUI_BASELINE, PACKAGE_NAME, SHELL_TITLE
from webcam_micro.camera import (
    CameraControl,
    CameraControlApplyError,
    CameraDescriptor,
    CameraOutputError,
    MissingCameraDependencyError,
    NullCameraBackend,
    PreviewFrame,
    QtCameraBackend,
    RecordingCropPlan,
    _choice_for_value,
    _preferred_recording_output_suffix,
    _safe_float,
    build_backend_plan,
    build_recording_file_filter,
    request_camera_permission,
)


class MissingGuiDependencyError(RuntimeError):
    """Raised when the GUI dependency set is not installed."""


PREVIEW_FRAMING_MODES = ("fit", "fill", "crop")
PREVIEW_FRAMING_LABELS = {
    "fit": "Fit",
    "fill": "Fill",
    "crop": "Crop",
}
DEFAULT_PREVIEW_SIZE = (960, 640)
WINDOWED_CONTENT_MARGINS = (16, 16, 16, 16)
WINDOWED_LAYOUT_SPACING = 12
DEFAULT_IMAGE_DIRECTORY = Path.home() / "microscope" / "images"
DEFAULT_VIDEO_DIRECTORY = Path.home() / "microscope" / "videos"
SETTINGS_IMAGE_DIRECTORY_KEY = "outputs/image_directory"
SETTINGS_VIDEO_DIRECTORY_KEY = "outputs/video_directory"
SETTINGS_SELECTED_CAMERA_KEY = "workspace/selected_camera_id"
SETTINGS_PREVIEW_FRAMING_KEY = "workspace/preview_framing_mode"
SETTINGS_CAPTURE_FRAMING_KEY = "workspace/capture_framing_mode"
SETTINGS_CONTROLS_VISIBLE_KEY = "workspace/controls_visible"
SETTINGS_FULLSCREEN_KEY = "workspace/fullscreen_enabled"
SETTINGS_FULLSCREEN_EXPANDED_KEY = "workspace/fullscreen_surface_expanded"
SETTINGS_WINDOW_GEOMETRY_KEY = "workspace/window_geometry"
SETTINGS_WINDOW_STATE_KEY = "workspace/window_state"
SETTINGS_CURRENT_PRESET_KEY = "workspace/current_preset_name"
SETTINGS_NAMED_PRESETS_KEY = "workspace/named_presets_json"
SETTINGS_DEFAULT_CONTROL_PREFIX = "defaults/"
SETTINGS_CAMERA_CONTROL_PREFIX = "camera/"
SETTINGS_SHORTCUT_PREFIX = "shortcuts/"
BUILTIN_CONTROL_DEFAULT_VALUES = {
    "brightness": 0,
    "contrast": 20,
    "saturation": 128,
    "hue": 0,
    "white_balance_automatic": False,
    "gamma": 72,
    "gain": 20,
    "power_line_frequency": 50,
    "white_balance_temperature": 2800,
    "sharpness": 0,
    "backlight_compensation": 0,
    "exposure_mode": "continuous_auto",
    "exposure_locked": False,
    "zoom_factor": 1.0,
}
PRIMARY_SHORTCUT_SPECS = (
    ("controls", "Controls", "Ctrl+Alt+C", "_toggle_controls_action"),
    ("refresh", "Refresh", "F5", "_refresh_action"),
    ("open", "Open", "Ctrl+O", "_open_action"),
    ("close_camera", "Close Camera", "Ctrl+W", "_close_camera_action"),
    ("fit", "Fit", "Ctrl+1", "_fit_action"),
    ("fill", "Fill", "Ctrl+2", "_fill_action"),
    ("crop", "Crop", "Ctrl+3", "_crop_action"),
    ("still", "Still Capture", "Ctrl+Shift+S", "_still_action"),
    ("record", "Record Toggle", "Ctrl+R", "_record_action"),
    ("fullscreen", "Fullscreen", "F11", "_fullscreen_action"),
    ("fullscreen_collapse", "Collapse Surface", "Ctrl+[", None),
    ("fullscreen_expand", "Expand Surface", "Ctrl+]", None),
    ("preferences", "Preferences", "Ctrl+,", "_preferences_action"),
)
CONTROL_SURFACE_HIDDEN_CONTROL_IDS = {
    "control_backend",
    "low_light_boost_support",
}
CONTROL_SURFACE_SECTION_BY_CONTROL_ID = {
    "active_format": "Source Info",
    "exposure_locked": "Exposure",
    "exposure_mode": "Exposure",
    "restore_auto_exposure": "Actions",
    "zoom_factor": "Zoom",
}
CONTROL_SURFACE_SECTION_BY_KIND = {
    "action": "Actions",
    "boolean": "Toggles",
    "enum": "Selections",
    "numeric": "Adjustments",
    "read_only": "Source Info",
}
CONTROL_SURFACE_SECTION_ORDER = (
    "Exposure",
    "Zoom",
    "Source Info",
    "Actions",
    "Adjustments",
    "Toggles",
    "Selections",
    "Other Controls",
)
STILL_FILE_FILTER = "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)"


@dataclass(frozen=True)
class ShellSpec:
    """Describe the working shape of the Qt Widgets shell."""

    title: str
    theme_mode: str
    hero_title: str
    hero_body: tuple[str, ...]
    command_sections: tuple[str, ...]
    toolbar_actions: tuple[str, ...]
    controls_surface_title: str
    status_template: str
    copyright_notice: str


def build_shell_spec() -> ShellSpec:
    """Return the Qt Widgets shell description."""

    backend_plan = build_backend_plan()
    return ShellSpec(
        title=SHELL_TITLE,
        theme_mode="light",
        hero_title=APP_NAME,
        hero_body=(
            "Preview-first microscope camera prototype workspace.",
            f"GUI baseline: {GUI_BASELINE}",
            "Backend baseline: " f"{backend_plan.first_device_backend_target}",
            "Qt Multimedia owns camera discovery and capture sessions while "
            "the workspace keeps microscope-specific framing in the preview.",
            "A native desktop menu bar and toolbar keep the primary command "
            "surface close to the preview workspace, camera controls live "
            "in a toggleable dock, still capture saves quietly to the "
            "configured folder, and camera controls are grouped into "
            "Exposure, Zoom, Source Info, and Actions sections while "
            "backend-only details stay out of the main surface. A tighter "
            "preview cadence keeps the newest frame close to live motion "
            "while native dialogs handle preferences, diagnostics, "
            "recording start or stop flows, and named presets.",
        ),
        command_sections=(
            "Menu Bar",
            "Toolbar",
            "Preview Workspace",
            "Controls Dock",
            "Status Bar",
        ),
        toolbar_actions=(
            "Controls",
            "Refresh",
            "Open",
            "Fit",
            "Fill",
            "Crop",
            "Still",
            "Record",
            "Fullscreen",
            "Preferences",
        ),
        controls_surface_title="Camera Controls",
        status_template=(
            "Backend: {backend} | Camera: {camera} | Source: {source} | "
            "Preview framing: {framing} | "
            "Capture framing: {capture_framing} | Controls: {controls} | "
            "Preset: {preset} | Recording: {recording} | {notice}"
        ),
        copyright_notice=(
            "© 2026 Black Epsilon Ltd. and " "Apostol Apostolov"
        ),
    )


@dataclass(frozen=True)
class RuntimeStatus:
    """Describe the visible runtime status shown in the main shell."""

    backend_name: str
    camera_name: str
    preview_state: str
    source_mode: str
    framing_mode: str
    capture_framing_mode: str
    controls_surface_state: str
    current_preset_name: str
    recording_state: str
    notice: str


def build_runtime_status(
    backend_name: str,
    camera_name: str,
    preview_state: str,
    source_mode: str,
    framing_mode: str,
    capture_framing_mode: str,
    controls_surface_state: str,
    current_preset_name: str,
    recording_state: str,
    notice: str,
) -> RuntimeStatus:
    """Return one visible runtime-status snapshot for the status bar."""

    return RuntimeStatus(
        backend_name=backend_name,
        camera_name=camera_name,
        preview_state=preview_state,
        source_mode=source_mode,
        framing_mode=framing_mode,
        capture_framing_mode=capture_framing_mode,
        controls_surface_state=controls_surface_state,
        current_preset_name=current_preset_name,
        recording_state=recording_state,
        notice=notice,
    )


@dataclass(frozen=True)
class RenderedPreview:
    """Describe how one source frame should render into the preview area."""

    width: int
    height: int
    source_x: int
    source_y: int
    source_width: int
    source_height: int

    @property
    def size(self) -> tuple[int, int]:
        """Return the rendered preview size as a tuple."""

        return (self.width, self.height)


def build_fullscreen_surface_actions(*, expanded: bool) -> tuple[str, ...]:
    """Describe the Qt baseline fullscreen action surface for one state."""

    if expanded:
        return (
            "Controls",
            "Still",
            "Record",
            "Preferences",
            "Fit",
            "Fill",
            "Crop",
            "Windowed",
            "Collapse",
        )
    return ("Expand", "Windowed")


def build_controls_surface_lines(
    *,
    backend_name: str,
    camera_name: str,
    preview_state: str,
    preview_framing_mode: str,
    capture_framing_mode: str,
    control_count: int,
) -> tuple[str, ...]:
    """Return the visible summary lines for the controls surface."""

    return (
        f"Backend: {backend_name}",
        f"Camera: {camera_name}",
        f"Preview: {preview_state}",
        f"Preview framing: {preview_framing_mode}",
        f"Capture framing: {capture_framing_mode}",
        f"Controls surfaced: {control_count}",
    )


def format_recording_duration(milliseconds: int) -> str:
    """Return one stable recording-duration label."""

    total_seconds = max(0, int(milliseconds) // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def build_diagnostics_lines(
    *,
    backend_name: str,
    camera_name: str,
    preview_state: str,
    source_mode: str,
    preview_framing_mode: str,
    capture_framing_mode: str,
    control_count: int,
    current_preset_name: str,
    recording_state: str,
    image_directory: str,
    video_directory: str,
    controls_surface_state: str,
    fullscreen_state: str,
    notice: str,
) -> tuple[str, ...]:
    """Return the visible diagnostics-report lines for one shell snapshot."""

    return (
        f"Backend: {backend_name}",
        f"Camera: {camera_name}",
        f"Preview: {preview_state}",
        f"Source mode: {source_mode}",
        f"Preview framing: {preview_framing_mode}",
        f"Capture framing: {capture_framing_mode}",
        f"Controls surfaced: {control_count}",
        f"Preset: {current_preset_name}",
        f"Controls dock: {controls_surface_state}",
        f"Fullscreen: {fullscreen_state}",
        f"Recording: {recording_state}",
        f"Image folder: {image_directory}",
        f"Video folder: {video_directory}",
        f"Notice: {notice}",
    )


def build_prototype_exit_check_lines(
    *,
    app_name: str,
    package_name: str,
    gui_baseline: str,
    backend_name: str,
    camera_name: str,
    preview_state: str,
    source_mode: str,
    preview_framing_mode: str,
    capture_framing_mode: str,
    controls_surface_state: str,
    fullscreen_state: str,
    current_preset_name: str,
    recording_state: str,
    image_directory: str,
    video_directory: str,
    diagnostic_event_count: int,
) -> tuple[str, ...]:
    """Return one release-readiness and exit-check report."""

    return (
        "Release readiness",
        f"Package: {package_name}",
        f"Entry point: {app_name}",
        "Python floor: 3.11+",
        f"GUI baseline: {gui_baseline}",
        "Build artifacts: governance-gated CI distributions",
        "Publish path: trusted publishing from validated CI artifacts",
        "",
        "Prototype exit checks",
        f"Backend: {backend_name}",
        f"Camera: {camera_name}",
        f"Preview state: {preview_state}",
        f"Source mode: {source_mode}",
        f"Preview framing: {preview_framing_mode}",
        f"Capture framing: {capture_framing_mode}",
        f"Controls dock: {controls_surface_state}",
        f"Fullscreen: {fullscreen_state}",
        f"Preset: {current_preset_name}",
        f"Recording: {recording_state}",
        f"Image folder: {image_directory}",
        f"Video folder: {video_directory}",
        f"Recent diagnostic events: {diagnostic_event_count}",
        "Recording containers are validated on this runtime.",
    )


def format_numeric_control_value(
    value: float,
    step: float | None,
) -> str:
    """Return a stable numeric string for sliders, labels, and fields."""

    if step is None:
        return f"{value:g}"
    if step >= 1:
        decimals = 0
    elif step >= 0.1:
        decimals = 1
    elif step >= 0.01:
        decimals = 2
    else:
        decimals = 3
    formatted = f"{value:.{decimals}f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


def parse_numeric_control_text(
    text: str,
    *,
    minimum: float,
    maximum: float,
) -> float | None:
    """Parse one numeric field value and reject invalid input as `None`."""

    stripped = text.strip()
    if not stripped:
        return None
    try:
        value = float(stripped)
    except ValueError:
        return None
    if value < minimum or value > maximum:
        return None
    return value


def _fit_preview_size(
    *,
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> tuple[int, int]:
    """Return the scaled size that fits one source inside the preview area."""

    scale = min(target_width / source_width, target_height / source_height)
    return (
        max(1, int(round(source_width * scale))),
        max(1, int(round(source_height * scale))),
    )


def _center_fill_crop(
    *,
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> tuple[int, int, int, int]:
    """Return the centered source crop that fills one preview rectangle."""

    target_ratio = target_width / target_height
    source_ratio = source_width / source_height
    if source_ratio > target_ratio:
        crop_width = max(1, int(round(source_height * target_ratio)))
        crop_height = source_height
        crop_x = max(0, (source_width - crop_width) // 2)
        crop_y = 0
    else:
        crop_width = source_width
        crop_height = max(1, int(round(source_width / target_ratio)))
        crop_x = 0
        crop_y = max(0, (source_height - crop_height) // 2)
    return (crop_x, crop_y, crop_width, crop_height)


def _center_square_crop(
    *,
    source_width: int,
    source_height: int,
) -> tuple[int, int, int, int]:
    """Return the centered microscope square crop from one source frame."""

    crop_size = min(source_width, source_height)
    return (
        max(0, (source_width - crop_size) // 2),
        max(0, (source_height - crop_size) // 2),
        crop_size,
        crop_size,
    )


def render_preview_image(
    *,
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
    framing_mode: str,
) -> RenderedPreview:
    """Return the crop and size plan for one preview framing mode."""

    source_width = max(1, int(source_width))
    source_height = max(1, int(source_height))
    target_width = max(1, int(target_width))
    target_height = max(1, int(target_height))
    if framing_mode == "fill":
        source_x, source_y, crop_width, crop_height = _center_fill_crop(
            source_width=source_width,
            source_height=source_height,
            target_width=target_width,
            target_height=target_height,
        )
        return RenderedPreview(
            width=target_width,
            height=target_height,
            source_x=source_x,
            source_y=source_y,
            source_width=crop_width,
            source_height=crop_height,
        )
    if framing_mode == "crop":
        source_x, source_y, crop_width, crop_height = _center_square_crop(
            source_width=source_width,
            source_height=source_height,
        )
        rendered_width, rendered_height = _fit_preview_size(
            source_width=crop_width,
            source_height=crop_height,
            target_width=target_width,
            target_height=target_height,
        )
        return RenderedPreview(
            width=rendered_width,
            height=rendered_height,
            source_x=source_x,
            source_y=source_y,
            source_width=crop_width,
            source_height=crop_height,
        )
    rendered_width, rendered_height = _fit_preview_size(
        source_width=source_width,
        source_height=source_height,
        target_width=target_width,
        target_height=target_height,
    )
    return RenderedPreview(
        width=rendered_width,
        height=rendered_height,
        source_x=0,
        source_y=0,
        source_width=source_width,
        source_height=source_height,
    )


def _timestamp_slug(now: datetime | None = None) -> str:
    """Return one compact local timestamp for output filenames."""

    current = datetime.now() if now is None else now
    return current.strftime("%Y%m%d-%H%M%S")


def _default_still_output_path(directory: Path) -> Path:
    """Return one default still-image output path."""

    return directory / f"microscope-{_timestamp_slug()}.png"


def _next_available_output_path(path: Path) -> Path:
    """Return one unused output path by appending a numeric suffix."""

    if not path.exists():
        return path
    candidate_index = 1
    while True:
        candidate = path.with_name(
            f"{path.stem}-{candidate_index}{path.suffix}"
        )
        if not candidate.exists():
            return candidate
        candidate_index += 1


def _default_recording_output_path(
    directory: Path,
    *,
    suffix: str = ".mp4",
) -> Path:
    """Return one default recording output path."""

    return directory / f"microscope-{_timestamp_slug()}{suffix}"


def _directory_setting_path(value: object, *, default: Path) -> Path:
    """Return one output-directory path from persisted settings."""

    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return Path(text).expanduser()


def _settings_text(value: object, *, default: str = "") -> str:
    """Return one compact persisted text value."""

    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text


def _settings_bool(value: object, *, default: bool) -> bool:
    """Return one persisted boolean value."""

    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _shortcut_text(value: object, *, default: str) -> str:
    """Return one persisted shortcut text token."""

    return _settings_text(value, default=default)


def _shortcut_key_text(shortcut_text: str) -> str:
    """Return the stable comparison text for one shortcut sequence."""

    text = shortcut_text.strip()
    if not text:
        return ""
    return text


def _control_default_setting_key(control_id: str) -> str:
    """Return one settings key for a global control default."""

    return f"{SETTINGS_DEFAULT_CONTROL_PREFIX}{control_id}"


def _camera_control_setting_key(
    descriptor_id: str,
    control_id: str,
) -> str:
    """Return one settings key for a per-camera remembered control."""

    return f"{SETTINGS_CAMERA_CONTROL_PREFIX}{descriptor_id}/{control_id}"


def _shortcut_setting_key(action_id: str) -> str:
    """Return one settings key for a primary shortcut."""

    return f"{SETTINGS_SHORTCUT_PREFIX}{action_id}"


def _named_presets_from_value(
    value: object,
) -> dict[str, dict[str, object]]:
    """Return the stored named presets as a dictionary."""

    text = _settings_text(value)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(payload, dict):
        return {}
    presets: dict[str, dict[str, object]] = {}
    for preset_name, snapshot in payload.items():
        if not isinstance(preset_name, str) or not isinstance(snapshot, dict):
            continue
        presets[preset_name] = snapshot
    return presets


def _named_presets_to_value(
    presets: dict[str, dict[str, object]],
) -> str:
    """Return one deterministic JSON payload for named presets."""

    return json.dumps(presets, sort_keys=True, separators=(",", ":"))


def _control_surface_section_name(control: CameraControl) -> str | None:
    """Return the visible controls-surface section for one control."""

    if control.control_id in CONTROL_SURFACE_HIDDEN_CONTROL_IDS:
        return None
    section = CONTROL_SURFACE_SECTION_BY_CONTROL_ID.get(control.control_id)
    if section is not None:
        return section
    return CONTROL_SURFACE_SECTION_BY_KIND.get(
        control.kind,
        "Other Controls",
    )


def _group_controls_for_surface(
    controls: tuple[CameraControl, ...],
) -> tuple[tuple[str, tuple[CameraControl, ...]], ...]:
    """Return the user-facing control groups in their display order."""

    grouped_controls: dict[str, list[CameraControl]] = {}
    for control in controls:
        section_name = _control_surface_section_name(control)
        if section_name is None:
            continue
        grouped_controls.setdefault(section_name, []).append(control)
    grouped_sections: list[tuple[str, tuple[CameraControl, ...]]] = []
    for section_name in CONTROL_SURFACE_SECTION_ORDER:
        section_controls = grouped_controls.pop(section_name, None)
        if section_controls:
            grouped_sections.append((section_name, tuple(section_controls)))
    for section_name in sorted(grouped_controls):
        section_controls = grouped_controls[section_name]
        if section_controls:
            grouped_sections.append((section_name, tuple(section_controls)))
    return tuple(grouped_sections)


def _persisted_control_value(
    control: CameraControl,
    value: object,
) -> object | None:
    """Return one persisted control value when it is valid for a control."""

    if control.kind == "boolean":
        return _settings_bool(value, default=bool(control.value))
    if control.kind == "numeric":
        numeric_value = _safe_float(value)
        if numeric_value is None:
            return None
        if control.min_value is not None and numeric_value < control.min_value:
            return None
        if control.max_value is not None and numeric_value > control.max_value:
            return None
        return numeric_value
    if control.kind == "enum":
        text_value = _settings_text(value)
        if not text_value:
            return None
        if _choice_for_value(control.choices, text_value) is None:
            return None
        return text_value
    return None


def _still_format_for_path(path: Path) -> str:
    """Return the image format token that matches one still filename."""

    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return "JPEG"
    return "PNG"


def _render_preview_pixmap(
    frame: PreviewFrame, *, plan: RenderedPreview, qt_core, qt_gui
):
    """Return one Qt pixmap rendered from a preview frame and crop plan."""

    qimage = qt_gui.QImage(
        frame.rgb_bytes,
        frame.width,
        frame.height,
        frame.width * 3,
        qt_gui.QImage.Format.Format_RGB888,
    ).copy()
    cropped = qimage.copy(
        plan.source_x,
        plan.source_y,
        plan.source_width,
        plan.source_height,
    )
    scaled = cropped.scaled(
        plan.width,
        plan.height,
        qt_core.Qt.AspectRatioMode.IgnoreAspectRatio,
        qt_core.Qt.TransformationMode.SmoothTransformation,
    )
    return qt_gui.QPixmap.fromImage(scaled)


def _capture_image_from_frame(
    frame: PreviewFrame,
    *,
    framing_mode: str,
    target_width: int,
    target_height: int,
    qt_gui,
):
    """Return one uncropped or cropped still image from the current frame."""

    source_image = qt_gui.QImage(
        frame.rgb_bytes,
        frame.width,
        frame.height,
        frame.width * 3,
        qt_gui.QImage.Format.Format_RGB888,
    ).copy()
    plan = render_preview_image(
        source_width=frame.width,
        source_height=frame.height,
        target_width=target_width,
        target_height=target_height,
        framing_mode=framing_mode,
    )
    return source_image.copy(
        plan.source_x,
        plan.source_y,
        plan.source_width,
        plan.source_height,
    )


def _recording_crop_plan_from_frame(
    frame: PreviewFrame,
    *,
    framing_mode: str,
    target_width: int,
    target_height: int,
) -> RecordingCropPlan:
    """Freeze the framed recording crop for the current live preview."""

    plan = render_preview_image(
        source_width=frame.width,
        source_height=frame.height,
        target_width=target_width,
        target_height=target_height,
        framing_mode=framing_mode,
    )
    return RecordingCropPlan(
        source_x=plan.source_x,
        source_y=plan.source_y,
        source_width=plan.source_width,
        source_height=plan.source_height,
    )


def _shortcut_conflict_label(
    shortcut_text_by_action: dict[str, str],
) -> str | None:
    """Return a human-readable shortcut conflict if one exists."""

    seen: dict[str, str] = {}
    for action_id, shortcut_text in shortcut_text_by_action.items():
        normalized = _shortcut_key_text(shortcut_text)
        if not normalized:
            continue
        previous = seen.get(normalized)
        if previous is not None:
            return f"{previous} and {action_id} share {normalized}."
        seen[normalized] = action_id
    return None


def _control_value_for_widget(
    control: CameraControl,
    value: object,
    *,
    qt_gui,
) -> object:
    """Return one widget-safe value for the control editor."""

    if control.kind == "boolean":
        return bool(value)
    if control.kind == "numeric":
        if value is None:
            return control.value
        try:
            return float(value)
        except (TypeError, ValueError):
            return control.value
    if control.kind == "enum":
        return _settings_text(value, default=str(control.value or ""))
    return value


def _control_value_for_storage(
    control: CameraControl,
    widget,
    *,
    qt_gui,
) -> object:
    """Return one persisted control value from a preferences widget."""

    if control.kind == "boolean":
        return bool(widget.isChecked())
    if control.kind == "numeric":
        return parse_numeric_control_text(
            widget.text(),
            minimum=control.min_value,
            maximum=control.max_value,
        )
    if control.kind == "enum":
        return widget.currentData()
    return None


def _numeric_decimals(step: float | None) -> int:
    """Return the number of decimals to show for one numeric control."""

    if step is None:
        return 3
    if step >= 1:
        return 0
    if step >= 0.1:
        return 1
    if step >= 0.01:
        return 2
    return 3


def _slider_scale(step: float | None) -> int:
    """Return the integer scale factor for one slider-backed value."""

    return 10 ** _numeric_decimals(step)


class PreviewApplication:
    """Manage camera discovery, preview, and controls in the Qt shell."""

    refresh_interval_milliseconds = 16

    def __init__(self, qt_core, qt_gui, qt_widgets, qt_application) -> None:
        """Build the Qt shell and initialize runtime state."""

        self._qt_core = qt_core
        self._qt_gui = qt_gui
        self._qt_widgets = qt_widgets
        self._application = qt_application
        self._spec = build_shell_spec()
        self._backend = self._build_backend()
        self._settings = qt_core.QSettings("apostolovbg", APP_NAME)
        self._session = None
        self._cameras: tuple[CameraDescriptor, ...] = ()
        self._selected_camera_id: str | None = None
        self._active_controls: tuple[CameraControl, ...] = ()
        self._controls_by_id: dict[str, CameraControl] = {}
        self._latest_frame: PreviewFrame | None = None
        self._last_frame_number = -1
        self._closed = False
        self._is_fullscreen = _settings_bool(
            self._settings.value(SETTINGS_FULLSCREEN_KEY),
            default=False,
        )
        self._fullscreen_surface_expanded = _settings_bool(
            self._settings.value(SETTINGS_FULLSCREEN_EXPANDED_KEY),
            default=True,
        )
        self._suspend_dock_sync = False
        self._controls_dock_requested = _settings_bool(
            self._settings.value(SETTINGS_CONTROLS_VISIBLE_KEY),
            default=True,
        )
        self._preview_state = "idle"
        self._preview_framing_mode = self._settings_mode_value(
            SETTINGS_PREVIEW_FRAMING_KEY,
            default="fit",
        )
        self._capture_framing_mode = self._settings_mode_value(
            SETTINGS_CAPTURE_FRAMING_KEY,
            default="fit",
        )
        self._named_presets = _named_presets_from_value(
            self._settings.value(SETTINGS_NAMED_PRESETS_KEY)
        )
        loaded_preset_name = _settings_text(
            self._settings.value(SETTINGS_CURRENT_PRESET_KEY),
            default="",
        )
        self._current_preset_name = (
            loaded_preset_name
            if loaded_preset_name in self._named_presets
            else None
        )
        self._selected_camera_id = (
            _settings_text(
                self._settings.value(SETTINGS_SELECTED_CAMERA_KEY),
                default="",
            )
            or None
        )
        self._recording_state = "not ready"
        self._image_directory = _directory_setting_path(
            self._settings.value(SETTINGS_IMAGE_DIRECTORY_KEY),
            default=DEFAULT_IMAGE_DIRECTORY,
        )
        self._video_directory = _directory_setting_path(
            self._settings.value(SETTINGS_VIDEO_DIRECTORY_KEY),
            default=DEFAULT_VIDEO_DIRECTORY,
        )
        self._last_recording_error: str | None = None
        self._status_notice = "Workspace ready."
        self._diagnostic_events: list[str] = []
        self._shortcut_text_by_action: dict[str, str] = {}

        self._window = None
        self._central_layout = None
        self._preview_stack = None
        self._preview_title_label = None
        self._preview_image_label = None
        self._preview_message_label = None
        self._workspace_notes = None
        self._status_label = None
        self._camera_combo = None
        self._controls_dock = None
        self._controls_summary_label = None
        self._controls_notice_label = None
        self._controls_body_widget = None
        self._controls_body_layout = None
        self._toggle_controls_action = None
        self._close_camera_action = None
        self._fit_action = None
        self._fill_action = None
        self._crop_action = None
        self._fullscreen_action = None
        self._window_toolbar = None
        self._fullscreen_surface = None
        self._fullscreen_surface_layout = None
        self._escape_shortcut = None
        self._preview_timer = None

        self._shortcut_actions: tuple[
            tuple[str, str, str, str | None], ...
        ] = PRIMARY_SHORTCUT_SPECS

        self._build_window()

    def _build_backend(self):
        """Return the active preview backend or a null fallback."""

        try:
            return QtCameraBackend()
        except MissingCameraDependencyError:
            return NullCameraBackend()

    def _settings_mode_value(self, key: str, *, default: str) -> str:
        """Return one persisted mode value from the settings store."""

        value = _settings_text(self._settings.value(key), default=default)
        if value not in PREVIEW_FRAMING_MODES:
            return default
        return value

    def _build_window(self) -> None:
        """Build the Qt Widgets preview-first workspace."""

        QtCore = self._qt_core
        QtWidgets = self._qt_widgets

        class ResizeAwareMainWindow(QtWidgets.QMainWindow):
            """Reposition fullscreen controls when the window resizes."""

            def __init__(self, on_resize) -> None:
                """Store one resize callback for the shell controller."""

                super().__init__()
                self._on_resize = on_resize

            def resizeEvent(self, event) -> None:  # pragma: no cover - Qt
                """Keep overlay controls anchored during fullscreen resizes."""

                super().resizeEvent(event)
                self._on_resize()

        self._window = ResizeAwareMainWindow(self._layout_fullscreen_surface)
        self._window.setWindowTitle(self._spec.title)
        self._window.resize(1080, 720)
        self._window.setMinimumSize(900, 640)

        central_widget = QtWidgets.QWidget()
        central_layout = QtWidgets.QVBoxLayout(central_widget)
        central_layout.setContentsMargins(*WINDOWED_CONTENT_MARGINS)
        central_layout.setSpacing(WINDOWED_LAYOUT_SPACING)
        self._central_layout = central_layout

        self._preview_title_label = QtWidgets.QLabel("Live Preview")
        self._preview_title_label.setObjectName("preview-title")
        central_layout.addWidget(self._preview_title_label)

        class ResizeAwareLabel(QtWidgets.QLabel):
            """Notify the controller whenever the preview area resizes."""

            def __init__(self, on_resize) -> None:
                """Keep a callback for resize-aware rerendering."""

                super().__init__()
                self._on_resize = on_resize

            def resizeEvent(self, event) -> None:  # pragma: no cover - Qt
                """Rerender the preview when the viewport size changes."""

                super().resizeEvent(event)
                self._on_resize()

        self._preview_image_label = ResizeAwareLabel(
            self._render_latest_preview
        )
        self._preview_image_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self._preview_image_label.setMinimumSize(320, 240)

        self._preview_message_label = QtWidgets.QLabel("Refreshing cameras...")
        self._preview_message_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self._preview_message_label.setWordWrap(True)

        self._preview_stack = QtWidgets.QStackedWidget()
        self._preview_stack.addWidget(self._preview_message_label)
        self._preview_stack.addWidget(self._preview_image_label)
        central_layout.addWidget(self._preview_stack, 1)

        self._workspace_notes = QtWidgets.QLabel(
            " ".join(self._spec.hero_body)
        )
        self._workspace_notes.setWordWrap(True)
        central_layout.addWidget(self._workspace_notes)

        self._window.setCentralWidget(central_widget)
        self._window.statusBar()

        self._build_controls_dock()
        self._build_actions()
        self._build_menu_bar()
        self._build_toolbar()
        self._build_fullscreen_surface()
        self._build_window_shortcuts()

        self._status_label = QtWidgets.QLabel()
        self._window.statusBar().addWidget(self._status_label, 1)
        self._restore_workspace_state()
        self._application.aboutToQuit.connect(self._handle_quit)
        self._sync_controls_summary()
        self._set_status("idle", notice="Workspace ready.")

    def _build_controls_dock(self) -> None:
        """Create the toggleable controls dock."""

        QtCore = self._qt_core
        QtWidgets = self._qt_widgets

        self._controls_dock = QtWidgets.QDockWidget(
            self._spec.controls_surface_title,
            self._window,
        )
        self._controls_dock.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
            | QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )

        dock_widget = QtWidgets.QWidget()
        dock_layout = QtWidgets.QVBoxLayout(dock_widget)
        dock_layout.setContentsMargins(12, 12, 12, 12)
        dock_layout.setSpacing(12)

        self._controls_summary_label = QtWidgets.QLabel()
        self._controls_summary_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        dock_layout.addWidget(self._controls_summary_label)

        self._controls_notice_label = QtWidgets.QLabel(
            "Open a camera to inspect the active control surface."
        )
        self._controls_notice_label.setWordWrap(True)
        dock_layout.addWidget(self._controls_notice_label)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        self._controls_body_widget = QtWidgets.QWidget()
        self._controls_body_layout = QtWidgets.QVBoxLayout(
            self._controls_body_widget
        )
        self._controls_body_layout.setContentsMargins(0, 0, 0, 0)
        self._controls_body_layout.setSpacing(12)
        scroll_area.setWidget(self._controls_body_widget)
        dock_layout.addWidget(scroll_area, 1)

        self._controls_dock.setWidget(dock_widget)
        self._controls_dock.visibilityChanged.connect(
            self._handle_controls_dock_visibility_changed
        )
        self._window.addDockWidget(
            QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
            self._controls_dock,
        )

    def _build_actions(self) -> None:
        """Create the shared actions used by menus and the toolbar."""

        QtGui = self._qt_gui

        self._toggle_controls_action = self._controls_dock.toggleViewAction()
        self._toggle_controls_action.setText("Controls")
        self._toggle_controls_action.triggered.connect(
            self._toggle_controls_dock
        )

        self._refresh_action = QtGui.QAction("Refresh", self._window)
        self._refresh_action.setShortcut(self._qt_gui.QKeySequence("F5"))
        self._refresh_action.triggered.connect(self._refresh_cameras_action)

        self._open_action = QtGui.QAction("Open", self._window)
        self._open_action.triggered.connect(self._open_selected_camera_action)

        self._close_camera_action = QtGui.QAction(
            "Close Camera",
            self._window,
        )
        self._close_camera_action.triggered.connect(self.close_session)

        self._fit_action = QtGui.QAction("Fit", self._window)
        self._fit_action.setCheckable(True)
        self._fit_action.triggered.connect(
            lambda _checked=False: self._set_preview_framing_mode("fit")
        )

        self._fill_action = QtGui.QAction("Fill", self._window)
        self._fill_action.setCheckable(True)
        self._fill_action.triggered.connect(
            lambda _checked=False: self._set_preview_framing_mode("fill")
        )

        self._crop_action = QtGui.QAction("Crop", self._window)
        self._crop_action.setCheckable(True)
        self._crop_action.triggered.connect(
            lambda _checked=False: self._set_preview_framing_mode("crop")
        )

        self._framing_action_group = QtGui.QActionGroup(self._window)
        self._framing_action_group.setExclusive(True)
        for action in (self._fit_action, self._fill_action, self._crop_action):
            self._framing_action_group.addAction(action)

        self._still_action = QtGui.QAction("Still", self._window)
        self._still_action.setShortcut(
            self._qt_gui.QKeySequence("Ctrl+Shift+S")
        )
        self._still_action.triggered.connect(self._capture_still_action)

        self._record_action = QtGui.QAction("Record", self._window)
        self._record_action.setShortcut(self._qt_gui.QKeySequence("Ctrl+R"))
        self._record_action.triggered.connect(self._toggle_recording_action)

        self._fullscreen_action = QtGui.QAction("Fullscreen", self._window)
        self._fullscreen_action.setCheckable(True)
        self._fullscreen_action.setShortcut(QtGui.QKeySequence("F11"))
        self._fullscreen_action.triggered.connect(self._toggle_fullscreen)

        self._preferences_action = QtGui.QAction("Preferences", self._window)
        self._preferences_action.setMenuRole(
            QtGui.QAction.MenuRole.PreferencesRole
        )
        self._preferences_action.triggered.connect(self._open_preferences)

        self._collapse_fullscreen_action = QtGui.QAction(
            "Collapse Fullscreen Surface",
            self._window,
        )
        self._collapse_fullscreen_action.triggered.connect(
            lambda _checked=False: self._set_fullscreen_surface_expanded(False)
        )

        self._expand_fullscreen_action = QtGui.QAction(
            "Expand Fullscreen Surface",
            self._window,
        )
        self._expand_fullscreen_action.triggered.connect(
            lambda _checked=False: self._set_fullscreen_surface_expanded(True)
        )

        self._diagnostics_action = QtGui.QAction("Diagnostics", self._window)
        self._diagnostics_action.triggered.connect(self._open_diagnostics)

        self._copy_status_action = QtGui.QAction(
            "Copy Status Summary", self._window
        )
        self._copy_status_action.setShortcut(
            self._qt_gui.QKeySequence.StandardKey.Copy
        )
        self._copy_status_action.triggered.connect(self._copy_status_summary)

        self._about_action = QtGui.QAction("About", self._window)
        self._about_action.setMenuRole(QtGui.QAction.MenuRole.AboutRole)
        self._about_action.triggered.connect(self._show_about)

        self._exit_action = QtGui.QAction("Exit", self._window)
        self._exit_action.setMenuRole(QtGui.QAction.MenuRole.QuitRole)
        self._exit_action.triggered.connect(self._window.close)

    def _build_menu_bar(self) -> None:
        """Build the native desktop menu bar."""

        menu_bar = self._window.menuBar()
        if hasattr(menu_bar, "setNativeMenuBar"):
            menu_bar.setNativeMenuBar(True)

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self._exit_action)

        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction(self._copy_status_action)

        view_menu = menu_bar.addMenu("View")
        view_menu.addAction(self._toggle_controls_action)
        view_menu.addSeparator()
        view_menu.addAction(self._fit_action)
        view_menu.addAction(self._fill_action)
        view_menu.addAction(self._crop_action)
        view_menu.addSeparator()
        view_menu.addAction(self._fullscreen_action)

        camera_menu = menu_bar.addMenu("Camera")
        camera_menu.addAction(self._refresh_action)
        camera_menu.addAction(self._open_action)
        camera_menu.addAction(self._close_camera_action)

        capture_menu = menu_bar.addMenu("Capture")
        capture_menu.addAction(self._still_action)
        capture_menu.addAction(self._record_action)

        tools_menu = menu_bar.addMenu("Tools")
        tools_menu.addAction(self._preferences_action)
        tools_menu.addAction(self._diagnostics_action)

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(self._about_action)

    def _build_toolbar(self) -> None:
        """Build the main toolbar for the Qt shell."""

        QtWidgets = self._qt_widgets

        toolbar = self._window.addToolBar("Main")
        toolbar.setMovable(False)
        self._window_toolbar = toolbar
        toolbar.addAction(self._toggle_controls_action)
        toolbar.addAction(self._refresh_action)

        self._camera_combo = QtWidgets.QComboBox()
        self._camera_combo.setMinimumContentsLength(28)
        self._camera_combo.currentIndexChanged.connect(
            self._handle_camera_index_changed
        )
        toolbar.addWidget(self._camera_combo)

        toolbar.addAction(self._open_action)
        toolbar.addAction(self._close_camera_action)
        toolbar.addSeparator()
        toolbar.addAction(self._fit_action)
        toolbar.addAction(self._fill_action)
        toolbar.addAction(self._crop_action)
        toolbar.addSeparator()
        toolbar.addAction(self._still_action)
        toolbar.addAction(self._record_action)
        toolbar.addAction(self._fullscreen_action)
        toolbar.addAction(self._preferences_action)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        toolbar.addWidget(spacer)
        toolbar.addWidget(QtWidgets.QLabel(self._spec.copyright_notice))

    def _build_fullscreen_surface(self) -> None:
        """Build the compact fullscreen command surface."""

        QtWidgets = self._qt_widgets

        self._fullscreen_surface = QtWidgets.QFrame(self._window)
        self._fullscreen_surface.setObjectName("fullscreen-surface")
        self._fullscreen_surface.setFrameShape(
            QtWidgets.QFrame.Shape.StyledPanel
        )
        self._fullscreen_surface.setStyleSheet(
            "QFrame#fullscreen-surface {"
            "background-color: rgba(28, 28, 28, 216);"
            "border: 1px solid rgba(255, 255, 255, 48);"
            "border-radius: 10px;"
            "}"
        )
        layout = QtWidgets.QHBoxLayout(self._fullscreen_surface)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        self._fullscreen_surface_layout = layout
        self._fullscreen_surface.hide()
        self._rebuild_fullscreen_surface()

    def _build_window_shortcuts(self) -> None:
        """Attach safe fullscreen shortcuts that outlive toolbar visibility."""

        self._escape_shortcut = self._qt_gui.QShortcut(
            self._qt_gui.QKeySequence("Escape"),
            self._window,
        )
        self._escape_shortcut.activated.connect(self._handle_escape_shortcut)

    def _restore_workspace_state(self) -> None:
        """Restore the persisted window and shortcut state."""

        geometry = self._settings.value(SETTINGS_WINDOW_GEOMETRY_KEY)
        if geometry is not None:
            self._window.restoreGeometry(geometry)
        window_state = self._settings.value(SETTINGS_WINDOW_STATE_KEY)
        if window_state is not None:
            self._window.restoreState(window_state)
        self._controls_dock.setVisible(self._controls_dock_requested)
        self._apply_persisted_shortcuts()
        if self._fullscreen_surface_expanded is not None:
            self._rebuild_fullscreen_surface()

    def _persist_workspace_state(self) -> None:
        """Store the current window and workspace preferences."""

        self._settings.setValue(
            SETTINGS_SELECTED_CAMERA_KEY,
            self._selected_camera_id or "",
        )
        self._settings.setValue(
            SETTINGS_PREVIEW_FRAMING_KEY,
            self._preview_framing_mode,
        )
        self._settings.setValue(
            SETTINGS_CAPTURE_FRAMING_KEY,
            self._capture_framing_mode,
        )
        self._settings.setValue(
            SETTINGS_CONTROLS_VISIBLE_KEY,
            self._controls_dock.isVisible(),
        )
        self._settings.setValue(
            SETTINGS_FULLSCREEN_KEY,
            self._is_fullscreen,
        )
        self._settings.setValue(
            SETTINGS_FULLSCREEN_EXPANDED_KEY,
            self._fullscreen_surface_expanded,
        )
        self._settings.setValue(
            SETTINGS_WINDOW_GEOMETRY_KEY,
            self._window.saveGeometry(),
        )
        self._settings.setValue(
            SETTINGS_WINDOW_STATE_KEY,
            self._window.saveState(),
        )
        self._settings.setValue(
            SETTINGS_IMAGE_DIRECTORY_KEY,
            str(self._image_directory),
        )
        self._settings.setValue(
            SETTINGS_VIDEO_DIRECTORY_KEY,
            str(self._video_directory),
        )
        self._settings.setValue(
            SETTINGS_CURRENT_PRESET_KEY,
            self._current_preset_name or "",
        )
        self._settings.setValue(
            SETTINGS_NAMED_PRESETS_KEY,
            _named_presets_to_value(self._named_presets),
        )
        self._persist_shortcuts()

    def _shortcut_action_for_id(self, action_id: str):
        """Return one QAction matching the persisted shortcut id."""

        action_name_map = {
            "controls": self._toggle_controls_action,
            "refresh": self._refresh_action,
            "open": self._open_action,
            "close_camera": self._close_camera_action,
            "fit": self._fit_action,
            "fill": self._fill_action,
            "crop": self._crop_action,
            "still": self._still_action,
            "record": self._record_action,
            "fullscreen": self._fullscreen_action,
            "fullscreen_collapse": self._collapse_fullscreen_action,
            "fullscreen_expand": self._expand_fullscreen_action,
            "preferences": self._preferences_action,
        }
        return action_name_map.get(action_id)

    def _load_shortcut_text(self, action_id: str, default_text: str) -> str:
        """Return one shortcut text from settings or the fallback value."""

        value = self._settings.value(_shortcut_setting_key(action_id))
        shortcut_text = _shortcut_text(value, default=default_text)
        return shortcut_text

    def _apply_shortcut_texts(
        self,
        shortcut_text_by_action: dict[str, str],
    ) -> None:
        """Apply one shortcut map to the editable primary actions."""

        for action_id, shortcut_text in shortcut_text_by_action.items():
            action = self._shortcut_action_for_id(action_id)
            if action is None:
                continue
            action.setShortcut(self._qt_gui.QKeySequence(shortcut_text))

    def _apply_persisted_shortcuts(self) -> None:
        """Restore the persisted shortcut map or its defaults."""

        shortcut_text_by_action = {}
        for (
            action_id,
            _label,
            default_text,
            _action_attr,
        ) in self._shortcut_actions:
            shortcut_text_by_action[action_id] = self._load_shortcut_text(
                action_id,
                default_text,
            )
        self._apply_shortcut_texts(shortcut_text_by_action)
        self._shortcut_text_by_action = shortcut_text_by_action

    def _persist_shortcuts(self) -> None:
        """Store the current shortcut texts for the editable actions."""

        shortcut_text_by_action = getattr(
            self,
            "_shortcut_text_by_action",
            {},
        )
        for action_id, shortcut_text in shortcut_text_by_action.items():
            self._settings.setValue(
                _shortcut_setting_key(action_id),
                shortcut_text,
            )

    def _current_preset_snapshot(self) -> dict[str, object]:
        """Return one named-preset snapshot from the live shell state."""

        controls: dict[str, object] = {}
        for control in self._active_controls:
            if control.value is None:
                continue
            controls[control.control_id] = control.value
        return {
            "preview_framing_mode": self._preview_framing_mode,
            "capture_framing_mode": self._capture_framing_mode,
            "controls": controls,
        }

    def _apply_named_preset(self, preset_name: str) -> bool:
        """Apply one named preset when the preset exists."""

        preset_name = _settings_text(preset_name)
        if not preset_name:
            return False
        preset = self._named_presets.get(preset_name)
        if preset is None:
            return False
        self._current_preset_name = preset_name
        preview_mode = _settings_text(
            preset.get("preview_framing_mode"),
            default=self._preview_framing_mode,
        )
        if preview_mode in PREVIEW_FRAMING_MODES:
            self._set_preview_framing_mode(preview_mode)
        capture_mode = _settings_text(
            preset.get("capture_framing_mode"),
            default=self._capture_framing_mode,
        )
        if capture_mode in PREVIEW_FRAMING_MODES:
            self._set_capture_framing_mode(capture_mode)
        descriptor = self._selected_descriptor()
        if descriptor is None:
            self._persist_workspace_state()
            return True
        control_values = preset.get("controls")
        if not isinstance(control_values, dict):
            self._persist_workspace_state()
            return True
        for control in self._active_controls:
            raw_value = control_values.get(control.control_id)
            value = _persisted_control_value(control, raw_value)
            if value is None:
                continue
            try:
                self._backend.set_control_value(
                    descriptor,
                    control.control_id,
                    value,
                )
            except CameraControlApplyError:
                continue
            self._settings.setValue(
                _camera_control_setting_key(
                    descriptor.stable_id,
                    control.control_id,
                ),
                value,
            )
        self._refresh_control_surface(notice=f"Applied preset {preset_name}.")
        self._set_status(
            self._preview_state,
            notice=f"Applied preset {preset_name}.",
        )
        self._persist_workspace_state()
        return True

    def _save_named_preset(self, preset_name: str) -> bool:
        """Store the live shell state under one preset name."""

        preset_name = _settings_text(preset_name)
        if not preset_name:
            return False
        self._named_presets[preset_name] = self._current_preset_snapshot()
        self._current_preset_name = preset_name
        self._persist_workspace_state()
        return True

    def _delete_named_preset(self, preset_name: str) -> bool:
        """Delete one stored named preset when it exists."""

        preset_name = _settings_text(preset_name)
        if not preset_name or preset_name not in self._named_presets:
            return False
        del self._named_presets[preset_name]
        if self._current_preset_name == preset_name:
            self._current_preset_name = None
        self._persist_workspace_state()
        return True

    def _make_fullscreen_surface_action_button(self, action):
        """Return one fullscreen-surface button bound to a shared action."""

        button = self._qt_widgets.QToolButton(self._fullscreen_surface)
        button.setToolButtonStyle(
            self._qt_core.Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        button.setAutoRaise(True)
        button.setDefaultAction(action)
        return button

    def _make_fullscreen_surface_command_button(
        self,
        *,
        label: str,
        handler,
    ):
        """Return one fullscreen-surface button for a local command."""

        button = self._qt_widgets.QToolButton(self._fullscreen_surface)
        button.setToolButtonStyle(
            self._qt_core.Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        button.setAutoRaise(True)
        button.setText(label)
        button.clicked.connect(handler)
        return button

    def _rebuild_fullscreen_surface(self) -> None:
        """Refresh the fullscreen command surface for its current state."""

        assert self._fullscreen_surface_layout is not None

        action_buttons = {
            "Controls": lambda: self._make_fullscreen_surface_action_button(
                self._toggle_controls_action
            ),
            "Still": lambda: self._make_fullscreen_surface_action_button(
                self._still_action
            ),
            "Record": lambda: self._make_fullscreen_surface_action_button(
                self._record_action
            ),
            "Preferences": lambda: (
                self._make_fullscreen_surface_action_button(
                    self._preferences_action
                )
            ),
            "Fit": lambda: self._make_fullscreen_surface_action_button(
                self._fit_action
            ),
            "Fill": lambda: self._make_fullscreen_surface_action_button(
                self._fill_action
            ),
            "Crop": lambda: self._make_fullscreen_surface_action_button(
                self._crop_action
            ),
            "Windowed": lambda: self._make_fullscreen_surface_command_button(
                label="Windowed",
                handler=lambda: self._set_fullscreen(False),
            ),
            "Collapse": lambda: self._make_fullscreen_surface_command_button(
                label="Collapse",
                handler=lambda: self._set_fullscreen_surface_expanded(False),
            ),
            "Expand": lambda: self._make_fullscreen_surface_command_button(
                label="Expand",
                handler=lambda: self._set_fullscreen_surface_expanded(True),
            ),
        }

        self._clear_layout(self._fullscreen_surface_layout)
        for action_name in build_fullscreen_surface_actions(
            expanded=self._fullscreen_surface_expanded
        ):
            self._fullscreen_surface_layout.addWidget(
                action_buttons[action_name]()
            )
        self._fullscreen_surface.adjustSize()
        self._layout_fullscreen_surface()

    def _layout_fullscreen_surface(self) -> None:
        """Anchor fullscreen controls near the top-right preview edge."""

        if self._fullscreen_surface is None:
            return
        if not self._is_fullscreen:
            self._fullscreen_surface.hide()
            return
        margin = 16
        size_hint = self._fullscreen_surface.sizeHint()
        self._fullscreen_surface.resize(size_hint)
        self._fullscreen_surface.move(
            max(margin, self._window.width() - size_hint.width() - margin),
            margin,
        )
        self._fullscreen_surface.show()
        self._fullscreen_surface.raise_()

    def _set_fullscreen_surface_expanded(self, expanded: bool) -> None:
        """Switch the fullscreen command surface between both shell states."""

        expanded = bool(expanded)
        if self._fullscreen_surface_expanded == expanded:
            return
        self._fullscreen_surface_expanded = expanded
        self._rebuild_fullscreen_surface()
        notice = (
            "Fullscreen controls expanded."
            if expanded
            else "Fullscreen controls collapsed."
        )
        self._set_status(self._preview_state, notice=notice)
        self._persist_workspace_state()

    def _handle_escape_shortcut(self) -> None:
        """Leave fullscreen safely when Escape is pressed."""

        if not self._is_fullscreen:
            return
        self._set_fullscreen(False)

    def _selected_descriptor(self) -> CameraDescriptor | None:
        """Return the currently selected camera descriptor, if any."""

        if self._selected_camera_id is None:
            return None
        for descriptor in self._cameras:
            if descriptor.stable_id == self._selected_camera_id:
                return descriptor
        return None

    def _controls_surface_state(self) -> str:
        """Return whether the controls dock is visible."""

        return "open" if not self._controls_dock.isHidden() else "closed"

    def _source_mode_label(self) -> str:
        """Return the current source-mode summary for the status bar."""

        if self._latest_frame is not None:
            width = self._latest_frame.width
            height = self._latest_frame.height
            return f"{width}x{height} live preview"
        width = getattr(self._backend, "preview_width", None)
        height = getattr(self._backend, "preview_height", None)
        if width is not None and height is not None:
            return f"{width}x{height}@30 preview"
        if self._backend.backend_name == "qt_multimedia":
            return "native live preview"
        return "unavailable"

    def _selected_camera_name(self) -> str:
        """Return the current camera label for the status surface."""

        descriptor = self._selected_descriptor()
        if descriptor is None:
            return "none"
        return descriptor.display_name

    def _fullscreen_state_label(self) -> str:
        """Return the current fullscreen state label for diagnostics."""

        if not self._is_fullscreen:
            return "windowed"
        if self._fullscreen_surface_expanded:
            return "fullscreen expanded"
        return "fullscreen collapsed"

    def _refresh_recording_state(self) -> None:
        """Mirror recorder state from the active session into the shell."""

        if self._session is None:
            self._recording_state = "not ready"
            self._last_recording_error = None
            return
        recording_error = self._session.recording_error
        if recording_error and recording_error != self._last_recording_error:
            self._last_recording_error = recording_error
            self._set_status(self._preview_state, notice=recording_error)
            self._record_diagnostic_event(recording_error)
        state = self._session.recording_state
        duration = self._session.recording_duration_milliseconds
        if state == "recording":
            self._recording_state = (
                "recording " f"{format_recording_duration(duration)}"
            )
            return
        if self._session.recording_output_path is not None and duration > 0:
            self._recording_state = (
                "saved " f"{format_recording_duration(duration)}"
            )
            return
        if self._session.recording_available:
            self._recording_state = "ready"
            return
        self._recording_state = "not ready"

    def _sync_action_states(self) -> None:
        """Keep menus and toolbar actions aligned with live session state."""

        has_session = self._session is not None
        has_frame = self._latest_frame is not None
        recording = bool(
            has_session and self._session.recording_state == "recording"
        )
        self._open_action.setEnabled(self._selected_descriptor() is not None)
        self._close_camera_action.setEnabled(has_session)
        self._still_action.setEnabled(has_frame)
        self._record_action.setEnabled(
            bool(has_session and self._session.recording_available)
        )
        self._record_action.setText(
            "Stop Recording" if recording else "Record"
        )

    def _current_diagnostics_lines(self) -> tuple[str, ...]:
        """Return the current diagnostics report for the visible shell."""

        return build_diagnostics_lines(
            backend_name=self._backend.backend_name,
            camera_name=self._selected_camera_name(),
            preview_state=self._preview_state,
            source_mode=self._source_mode_label(),
            preview_framing_mode=self._preview_framing_mode,
            capture_framing_mode=self._capture_framing_mode,
            control_count=len(self._active_controls),
            current_preset_name=self._current_preset_name or "none",
            recording_state=self._recording_state,
            image_directory=str(self._image_directory),
            video_directory=str(self._video_directory),
            controls_surface_state=self._controls_surface_state(),
            fullscreen_state=self._fullscreen_state_label(),
            notice=self._status_notice,
        )

    def _record_diagnostic_event(self, message: str) -> None:
        """Store one recoverable failure or notable runtime event."""

        text = _settings_text(message)
        if not text:
            return
        entry = f"{datetime.now().strftime('%H:%M:%S')} {text}"
        if self._diagnostic_events and self._diagnostic_events[-1] == entry:
            return
        self._diagnostic_events.append(entry)
        if len(self._diagnostic_events) > 24:
            self._diagnostic_events = self._diagnostic_events[-24:]

    def _diagnostic_log_lines(self) -> tuple[str, ...]:
        """Return the current diagnostic-event log for the shell."""

        if not self._diagnostic_events:
            return ("No recoverable failures have been recorded yet.",)
        return tuple(self._diagnostic_events)

    def _current_exit_check_lines(self) -> tuple[str, ...]:
        """Return the current release-readiness and exit-check report."""

        return build_prototype_exit_check_lines(
            app_name=APP_NAME,
            package_name=PACKAGE_NAME,
            gui_baseline=GUI_BASELINE,
            backend_name=self._backend.backend_name,
            camera_name=self._selected_camera_name(),
            preview_state=self._preview_state,
            source_mode=self._source_mode_label(),
            preview_framing_mode=self._preview_framing_mode,
            capture_framing_mode=self._capture_framing_mode,
            controls_surface_state=self._controls_surface_state(),
            fullscreen_state=self._fullscreen_state_label(),
            current_preset_name=self._current_preset_name or "none",
            recording_state=self._recording_state,
            image_directory=str(self._image_directory),
            video_directory=str(self._video_directory),
            diagnostic_event_count=len(self._diagnostic_events),
        )

    def _select_output_path(
        self,
        *,
        title: str,
        initial_path: Path,
        filter_text: str,
    ) -> Path | None:
        """Open one native save dialog for a recording path."""

        initial_path.parent.mkdir(parents=True, exist_ok=True)
        selected_path, _selected_filter = (
            self._qt_widgets.QFileDialog.getSaveFileName(
                self._window,
                title,
                str(initial_path),
                filter_text,
            )
        )
        if not selected_path:
            return None
        return Path(selected_path)

    def _set_controls_notice(self, message: str) -> None:
        """Update the controls-dock notice text."""

        self._controls_notice_label.setText(message)

    def _sync_controls_summary(self) -> None:
        """Refresh the controls-dock summary text."""

        lines = build_controls_surface_lines(
            backend_name=self._backend.backend_name,
            camera_name=self._selected_camera_name(),
            preview_state=self._preview_state,
            preview_framing_mode=self._preview_framing_mode,
            capture_framing_mode=self._capture_framing_mode,
            control_count=len(self._active_controls),
        )
        self._controls_summary_label.setText("\n".join(lines))

    def _set_capture_framing_mode(self, framing_mode: str) -> None:
        """Switch capture framing without changing the live preview mode."""

        if framing_mode not in PREVIEW_FRAMING_MODES:
            return
        self._capture_framing_mode = framing_mode
        self._sync_controls_summary()
        self._set_status(
            self._preview_state,
            notice=(
                f"{PREVIEW_FRAMING_LABELS[framing_mode]} capture framing "
                "active."
            ),
        )
        self._persist_workspace_state()

    def _controls_section_heading(self, heading: str):
        """Build one controls-dock section heading."""

        label = self._qt_widgets.QLabel(heading)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        return label

    def _control_details_text(self, control: CameraControl):
        """Return one optional helper label for a control."""

        if not control.details:
            return None
        details = self._qt_widgets.QLabel(control.details)
        details.setWordWrap(True)
        return details

    def _clear_layout(self, layout) -> None:
        """Remove all child widgets from one layout."""

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _rebuild_controls_widgets(self) -> None:
        """Render the current control surface into the Qt dock."""

        self._clear_layout(self._controls_body_layout)
        if not self._active_controls:
            self._controls_body_layout.addWidget(
                self._qt_widgets.QLabel(
                    "No camera controls are currently available for the "
                    "selected camera/backend."
                )
            )
            self._controls_body_layout.addStretch(1)
            return

        builder_by_kind = {
            "numeric": self._build_numeric_control,
            "boolean": self._build_boolean_control,
            "enum": self._build_enum_control,
            "read_only": self._build_read_only_control,
            "action": self._build_action_control,
        }
        for heading, controls in _group_controls_for_surface(
            self._active_controls
        ):
            self._controls_body_layout.addWidget(
                self._controls_section_heading(heading)
            )
            for control in controls:
                builder = builder_by_kind.get(control.kind)
                if builder is None:
                    continue
                widget = builder(control)
                if widget is not None:
                    self._controls_body_layout.addWidget(widget)
        self._controls_body_layout.addStretch(1)

    def _numeric_divisions(self, control: CameraControl) -> int | None:
        """Return safe slider divisions for one numeric control."""

        if (
            control.step is None
            or control.min_value is None
            or control.max_value is None
            or control.step <= 0
        ):
            return None
        step_count = (control.max_value - control.min_value) / control.step
        if step_count <= 0 or step_count > 1000:
            return None
        if not math.isclose(step_count, round(step_count), abs_tol=1e-6):
            return None
        return int(round(step_count))

    def _build_numeric_control(self, control: CameraControl):
        """Build one numeric camera-control dock row."""

        if (
            control.min_value is None
            or control.max_value is None
            or control.value is None
        ):
            return None

        QtCore = self._qt_core
        QtWidgets = self._qt_widgets

        scale = _slider_scale(control.step)
        step = control.step if control.step is not None else 1.0
        decimals = _numeric_decimals(control.step)
        disabled = control.read_only or not control.enabled

        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)

        label = QtWidgets.QLabel(control.label)
        container_layout.addWidget(label)

        slider_row = QtWidgets.QHBoxLayout()
        slider_row.setContentsMargins(0, 0, 0, 0)
        slider_row.setSpacing(12)

        slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        slider.setMinimum(int(round(control.min_value * scale)))
        slider.setMaximum(int(round(control.max_value * scale)))
        slider.setSingleStep(max(1, int(round(step * scale))))
        slider.setPageStep(max(1, int(round(step * scale * 5))))
        slider.setValue(int(round(float(control.value) * scale)))
        slider.setDisabled(disabled)
        slider_row.addWidget(slider, 1)

        editor_column = QtWidgets.QVBoxLayout()
        editor_column.setContentsMargins(0, 0, 0, 0)
        editor_column.setSpacing(2)

        value_field = QtWidgets.QLineEdit(
            format_numeric_control_value(float(control.value), control.step)
        )
        value_field.setFixedWidth(96)
        value_field.setDisabled(disabled)
        editor_column.addWidget(value_field)

        step_buttons = QtWidgets.QHBoxLayout()
        step_buttons.setContentsMargins(0, 0, 0, 0)
        step_buttons.setSpacing(2)

        step_up_button = QtWidgets.QToolButton()
        step_up_button.setText("^")
        step_up_button.setDisabled(disabled)
        step_buttons.addWidget(step_up_button)

        step_down_button = QtWidgets.QToolButton()
        step_down_button.setText("v")
        step_down_button.setDisabled(disabled)
        step_buttons.addWidget(step_down_button)

        editor_column.addLayout(step_buttons)
        slider_row.addLayout(editor_column)
        container_layout.addLayout(slider_row)

        midpoint = (control.min_value + control.max_value) / 2
        labels_row = QtWidgets.QHBoxLayout()
        labels_row.setContentsMargins(0, 0, 0, 0)
        labels_row.setSpacing(0)

        min_label = QtWidgets.QLabel(
            format_numeric_control_value(control.min_value, control.step)
        )
        mid_label = QtWidgets.QLabel(
            format_numeric_control_value(midpoint, control.step)
        )
        max_label = QtWidgets.QLabel(
            format_numeric_control_value(control.max_value, control.step)
        )
        min_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        mid_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        max_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        labels_row.addWidget(min_label)
        labels_row.addWidget(mid_label, 1)
        labels_row.addWidget(max_label)
        container_layout.addLayout(labels_row)

        details = self._control_details_text(control)
        if details is not None:
            container_layout.addWidget(details)

        # Keep the typed field aligned with slider-driven motion.
        def sync_field(numeric_value: float) -> None:
            was_blocked = value_field.blockSignals(True)
            value_field.setText(
                format_numeric_control_value(numeric_value, control.step)
            )
            value_field.blockSignals(was_blocked)

        # Keep the slider aligned when the field or step buttons change.
        def sync_slider(numeric_value: float) -> None:
            was_blocked = slider.blockSignals(True)
            slider.setValue(int(round(numeric_value * scale)))
            slider.blockSignals(was_blocked)

        # Mirror live slider motion into the adjacent numeric field.
        def handle_slider_change(raw_value: int) -> None:
            numeric_value = raw_value / scale
            sync_field(numeric_value)

        # Apply the current slider value once the user commits the drag.
        def handle_slider_commit() -> None:
            numeric_value = slider.value() / scale
            self._apply_control_value(
                control.control_id,
                numeric_value,
                refresh_surface=False,
                status_notice=False,
            )

        # Accept valid typed input and blank out invalid numeric text.
        def handle_field_commit() -> None:
            numeric_value = parse_numeric_control_text(
                value_field.text(),
                minimum=control.min_value,
                maximum=control.max_value,
            )
            if numeric_value is None:
                value_field.clear()
                message = f"{control.label} cleared an invalid value."
                self._set_controls_notice(message)
                self._set_status(self._preview_state, notice=message)
                self._record_diagnostic_event(message)
                return
            sync_slider(numeric_value)
            sync_field(numeric_value)
            self._apply_control_value(
                control.control_id,
                numeric_value,
                refresh_surface=False,
                status_notice=False,
            )

        # Nudge the value by one declared control step in either direction.
        def handle_step(direction: int) -> None:
            numeric_value = slider.value() / scale
            numeric_value += step * direction
            numeric_value = min(
                control.max_value,
                max(control.min_value, numeric_value),
            )
            numeric_value = round(numeric_value, decimals)
            sync_slider(numeric_value)
            sync_field(numeric_value)
            self._apply_control_value(
                control.control_id,
                numeric_value,
                refresh_surface=False,
                status_notice=False,
            )

        slider.valueChanged.connect(handle_slider_change)
        slider.sliderReleased.connect(handle_slider_commit)
        value_field.editingFinished.connect(handle_field_commit)
        step_up_button.clicked.connect(lambda: handle_step(1))
        step_down_button.clicked.connect(lambda: handle_step(-1))
        return container

    def _build_boolean_control(self, control: CameraControl):
        """Build one boolean camera-control dock row."""

        QtWidgets = self._qt_widgets

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        checkbox = QtWidgets.QCheckBox(control.label)
        checkbox.setChecked(bool(control.value))
        checkbox.setDisabled(control.read_only or not control.enabled)
        checkbox.toggled.connect(
            lambda checked, cid=control.control_id: (
                self._handle_boolean_toggle(cid, checked)
            )
        )
        layout.addWidget(checkbox)

        details = self._control_details_text(control)
        if details is not None:
            layout.addWidget(details)
        return container

    def _build_enum_control(self, control: CameraControl):
        """Build one enum camera-control dock row."""

        QtWidgets = self._qt_widgets

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QtWidgets.QLabel(control.label)
        layout.addWidget(label)

        dropdown = QtWidgets.QComboBox()
        for choice in control.choices:
            dropdown.addItem(choice.label, choice.value)
        if control.value is not None:
            index = dropdown.findData(str(control.value))
            if index >= 0:
                dropdown.setCurrentIndex(index)
        dropdown.setDisabled(control.read_only or not control.enabled)
        dropdown.currentIndexChanged.connect(
            lambda _index, cid=control.control_id, widget=dropdown: (
                self._handle_enum_selected(cid, widget.currentData())
            )
        )
        layout.addWidget(dropdown)

        details = self._control_details_text(control)
        if details is not None:
            layout.addWidget(details)
        return container

    def _build_read_only_control(self, control: CameraControl):
        """Build one read-only camera-control dock row."""

        QtWidgets = self._qt_widgets

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(QtWidgets.QLabel(f"{control.label}:"))
        layout.addWidget(QtWidgets.QLabel(str(control.value)))
        details = self._control_details_text(control)
        if details is not None:
            layout.addWidget(details)
        return container

    def _build_action_control(self, control: CameraControl):
        """Build one action camera-control dock row."""

        QtWidgets = self._qt_widgets

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        button = QtWidgets.QPushButton(control.action_label or control.label)
        button.setDisabled(control.read_only or not control.enabled)
        button.clicked.connect(
            lambda _checked=False, cid=control.control_id: (
                self._trigger_control_action(cid)
            )
        )
        layout.addWidget(button)

        details = self._control_details_text(control)
        if details is not None:
            layout.addWidget(details)
        return container

    def _refresh_control_surface(self, *, notice: str | None = None) -> None:
        """Reload the control surface for the selected camera."""

        descriptor = self._selected_descriptor()
        if descriptor is None:
            self._active_controls = ()
            self._controls_by_id = {}
            self._set_controls_notice(
                notice
                or "Select and open a camera to inspect camera controls."
            )
            self._sync_controls_summary()
            self._rebuild_controls_widgets()
            return
        try:
            controls = self._backend.list_controls(descriptor)
        except CameraControlApplyError as exc:
            self._active_controls = ()
            self._controls_by_id = {}
            self._set_controls_notice(str(exc))
            self._record_diagnostic_event(str(exc))
        else:
            self._active_controls = controls
            self._controls_by_id = {
                control.control_id: control for control in controls
            }
            if notice is not None:
                self._set_controls_notice(notice)
            elif controls:
                self._set_controls_notice(
                    "Controls reflect the active camera/backend and update "
                    "live where supported."
                )
            else:
                self._set_controls_notice(
                    "No camera controls are available for the selected "
                    "camera/backend."
                )
        self._sync_controls_summary()
        self._rebuild_controls_widgets()

    def _apply_control_value(
        self,
        control_id: str,
        value: object,
        *,
        refresh_surface: bool,
        status_notice: bool,
    ) -> None:
        """Apply one control value and refresh the surface when needed."""

        descriptor = self._selected_descriptor()
        control = self._controls_by_id.get(control_id)
        if descriptor is None or control is None:
            return
        try:
            self._backend.set_control_value(descriptor, control_id, value)
        except CameraControlApplyError as exc:
            self._set_controls_notice(str(exc))
            self._set_status(self._preview_state, notice=str(exc))
            self._record_diagnostic_event(str(exc))
            return
        self._settings.setValue(
            _camera_control_setting_key(descriptor.stable_id, control_id),
            value,
        )
        message = f"Updated {control.label}."
        self._set_controls_notice(message)
        if status_notice:
            self._set_status(self._preview_state, notice=message)
        if refresh_surface:
            self._refresh_control_surface(notice=message)

    def _apply_persisted_control_state(self) -> None:
        """Apply built-in, user, and remembered control values."""

        descriptor = self._selected_descriptor()
        if descriptor is None or self._session is None:
            return
        if not self._active_controls:
            return
        applied_controls: list[str] = []
        for control in self._active_controls:
            if control.read_only or not control.enabled:
                continue
            value = BUILTIN_CONTROL_DEFAULT_VALUES.get(control.control_id)
            stored_default = self._settings.value(
                _control_default_setting_key(control.control_id)
            )
            if stored_default is not None:
                value = stored_default
            stored_camera_value = self._settings.value(
                _camera_control_setting_key(
                    descriptor.stable_id,
                    control.control_id,
                )
            )
            if stored_camera_value is not None:
                value = stored_camera_value
            if value is None:
                continue
            try:
                self._backend.set_control_value(
                    descriptor, control.control_id, value
                )
            except CameraControlApplyError:
                continue
            applied_controls.append(control.control_id)
        if applied_controls:
            self._refresh_control_surface(
                notice="Applied saved camera settings."
            )

    def _handle_boolean_toggle(self, control_id: str, value: object) -> None:
        """Apply one boolean control from its check-box state."""

        self._apply_control_value(
            control_id,
            bool(value),
            refresh_surface=True,
            status_notice=True,
        )

    def _handle_enum_selected(self, control_id: str, value: object) -> None:
        """Apply one enum control from the current combo-box value."""

        if value is None:
            return
        self._apply_control_value(
            control_id,
            value,
            refresh_surface=True,
            status_notice=True,
        )

    def _trigger_control_action(self, control_id: str) -> None:
        """Trigger one action control and then refresh the surface."""

        descriptor = self._selected_descriptor()
        control = self._controls_by_id.get(control_id)
        if descriptor is None or control is None:
            return
        try:
            self._backend.trigger_control_action(descriptor, control_id)
        except CameraControlApplyError as exc:
            self._set_controls_notice(str(exc))
            self._set_status(self._preview_state, notice=str(exc))
            self._record_diagnostic_event(str(exc))
            return
        message = f"Triggered {control.label}."
        self._refresh_control_surface(notice=message)
        self._set_status(self._preview_state, notice=message)

    def _set_status(
        self,
        preview_state: str,
        *,
        notice: str | None = None,
    ) -> None:
        """Render the current backend, camera, and preview state."""

        if notice is not None:
            self._status_notice = notice
        self._preview_state = preview_state
        status = build_runtime_status(
            backend_name=self._backend.backend_name,
            camera_name=self._selected_camera_name(),
            preview_state=preview_state,
            source_mode=self._source_mode_label(),
            framing_mode=self._preview_framing_mode,
            capture_framing_mode=self._capture_framing_mode,
            controls_surface_state=self._controls_surface_state(),
            current_preset_name=self._current_preset_name or "none",
            recording_state=self._recording_state,
            notice=self._status_notice,
        )
        self._status_label.setText(
            self._spec.status_template.format(
                backend=status.backend_name,
                camera=status.camera_name,
                source=status.source_mode,
                framing=status.framing_mode,
                capture_framing=status.capture_framing_mode,
                controls=status.controls_surface_state,
                preset=status.current_preset_name,
                recording=status.recording_state,
                notice=status.notice,
            )
        )
        self._sync_controls_summary()
        self._sync_action_states()

    def _set_preview_message(self, message: str) -> None:
        """Show preview status text and clear any stale frame image."""

        self._latest_frame = None
        self._preview_message_label.setText(message)
        self._preview_stack.setCurrentWidget(self._preview_message_label)
        self._sync_controls_summary()

    def _preview_target_size(self) -> tuple[int, int]:
        """Return the current preview area size or a safe fallback."""

        if self._preview_image_label is None:
            return DEFAULT_PREVIEW_SIZE
        width = self._preview_image_label.width()
        height = self._preview_image_label.height()
        if width <= 1 or height <= 1:
            return DEFAULT_PREVIEW_SIZE
        return (width, height)

    def _render_latest_preview(self) -> None:
        """Render the newest cached frame using the active framing mode."""

        if self._latest_frame is None:
            return
        target_width, target_height = self._preview_target_size()
        rendered = render_preview_image(
            source_width=self._latest_frame.width,
            source_height=self._latest_frame.height,
            target_width=target_width,
            target_height=target_height,
            framing_mode=self._preview_framing_mode,
        )
        pixmap = _render_preview_pixmap(
            self._latest_frame,
            plan=rendered,
            qt_core=self._qt_core,
            qt_gui=self._qt_gui,
        )
        self._preview_image_label.setPixmap(pixmap)
        self._preview_stack.setCurrentWidget(self._preview_image_label)

    def refresh_cameras(self, *, auto_open: bool) -> None:
        """Refresh the discovered camera list and optionally open one."""

        self.close_session()
        self._cameras = self._backend.discover_cameras()

        was_blocked = self._camera_combo.blockSignals(True)
        self._camera_combo.clear()
        for descriptor in self._cameras:
            self._camera_combo.addItem(
                descriptor.display_name,
                descriptor.stable_id,
            )
        self._camera_combo.blockSignals(was_blocked)

        if not self._cameras:
            self._selected_camera_id = None
            self._active_controls = ()
            self._controls_by_id = {}
            if self._backend.backend_name == "null":
                self._set_preview_message(
                    "Camera runtime backend is unavailable.\n"
                    "Install package runtime dependencies and relaunch."
                )
            else:
                self._set_preview_message(
                    "No cameras detected.\nConnect a camera and refresh."
                )
            self._refresh_control_surface(notice="No camera devices detected.")
            self._set_status(
                "no devices", notice="No camera devices detected."
            )
            self._record_diagnostic_event("No camera devices detected.")
            self._persist_workspace_state()
            return

        selected_index = 0
        if self._selected_camera_id is not None:
            for index, descriptor in enumerate(self._cameras):
                if descriptor.stable_id == self._selected_camera_id:
                    selected_index = index
                    break
        self._selected_camera_id = self._cameras[selected_index].stable_id
        was_blocked = self._camera_combo.blockSignals(True)
        self._camera_combo.setCurrentIndex(selected_index)
        self._camera_combo.blockSignals(was_blocked)
        self._set_preview_message("Opening camera...")
        self._refresh_control_surface(notice="Camera list refreshed.")
        self._set_status("camera ready", notice="Camera list refreshed.")
        self._persist_workspace_state()
        if auto_open:
            self.open_selected_camera()

    def _handle_camera_index_changed(self, index: int) -> None:
        """Handle a camera selection change from the combo box."""

        if index < 0 or index >= len(self._cameras):
            return
        self._selected_camera_id = self._cameras[index].stable_id
        self._persist_workspace_state()
        self.open_selected_camera()

    def open_selected_camera(self) -> None:
        """Open the chosen camera and start preview updates."""

        descriptor = self._selected_descriptor()
        if descriptor is None:
            self._set_preview_message("No camera selected.")
            self._refresh_control_surface(notice="Choose a camera first.")
            self._set_status("no selection", notice="Choose a camera first.")
            self._record_diagnostic_event("No camera selected.")
            return
        granted, permission_notice = request_camera_permission(
            self._qt_core,
        )
        if not granted:
            notice = (
                permission_notice
                or "Camera access was denied before opening the camera."
            )
            if self._session is None:
                self._set_preview_message(notice)
            self._refresh_control_surface(notice=notice)
            self._set_status("permission denied", notice=notice)
            self._record_diagnostic_event(notice)
            return
        self.close_session()
        try:
            self._session = self._backend.open_session(descriptor)
        except RuntimeError as exc:
            self._set_preview_message(str(exc))
            self._refresh_control_surface(notice=str(exc))
            self._set_status("open failed", notice="Camera open failed.")
            self._record_diagnostic_event(str(exc))
            return
        self._refresh_recording_state()
        self._set_preview_message("Waiting for live preview frames...")
        self._refresh_control_surface(notice="Loaded camera controls.")
        self._apply_persisted_control_state()
        if self._current_preset_name is not None:
            if not self._apply_named_preset(self._current_preset_name):
                self._record_diagnostic_event(
                    f"Missing preset: {self._current_preset_name}."
                )
                self._current_preset_name = None
                self._persist_workspace_state()
        else:
            self._set_status("opening", notice="Opening selected camera.")
        self._poll_preview_frame()

    def _poll_preview_frame(self) -> None:
        """Poll the newest frame and refresh the preview without lagging."""

        if self._closed or self._session is None:
            return
        previous_recording_state = self._recording_state
        self._refresh_recording_state()
        failure_reason = self._session.failure_reason
        if failure_reason:
            self._set_preview_message(failure_reason)
            self._set_status(
                "preview failed",
                notice="Preview failed; see on-screen error.",
            )
            self._record_diagnostic_event(failure_reason)
            return
        frame = self._session.get_latest_frame()
        if self._recording_state != previous_recording_state:
            self._set_status(self._preview_state)
        if frame is None or frame.frame_number == self._last_frame_number:
            return
        self._last_frame_number = frame.frame_number
        self._latest_frame = frame
        self._render_latest_preview()
        self._set_status("live", notice="Live preview active.")

    def close_session(self) -> None:
        """Close the current camera session if one is active."""

        if self._session is None:
            return
        self._session.close()
        self._session = None
        self._latest_frame = None
        self._last_frame_number = -1
        self._refresh_recording_state()
        self._set_preview_message(
            "Camera closed.\nOpen a camera to restart preview."
        )
        self._refresh_control_surface(notice="Camera session closed.")
        self._set_status("closed", notice="Camera session closed.")
        self._sync_controls_summary()

    def _set_preview_framing_mode(self, framing_mode: str) -> None:
        """Switch preview framing live and rerender the latest frame."""

        if framing_mode not in PREVIEW_FRAMING_MODES:
            return
        self._preview_framing_mode = framing_mode
        self._fit_action.setChecked(framing_mode == "fit")
        self._fill_action.setChecked(framing_mode == "fill")
        self._crop_action.setChecked(framing_mode == "crop")
        self._render_latest_preview()
        self._set_status(
            self._preview_state,
            notice=(
                f"{PREVIEW_FRAMING_LABELS[framing_mode]} preview framing "
                "active."
            ),
        )
        self._persist_workspace_state()

    def _set_fullscreen(self, enabled: bool) -> None:
        """Enter or leave fullscreen mode through the native Qt window."""

        self._is_fullscreen = enabled
        self._fullscreen_action.setChecked(enabled)
        if enabled:
            self._central_layout.setContentsMargins(0, 0, 0, 0)
            self._central_layout.setSpacing(0)
            self._preview_title_label.hide()
            self._workspace_notes.hide()
            self._window_toolbar.hide()
            self._window.statusBar().hide()
            self._suspend_dock_sync = True
            self._controls_dock.hide()
            self._suspend_dock_sync = False
            self._window.showFullScreen()
            self._rebuild_fullscreen_surface()
            notice = "Fullscreen view active."
        else:
            self._window.showNormal()
            self._central_layout.setContentsMargins(*WINDOWED_CONTENT_MARGINS)
            self._central_layout.setSpacing(WINDOWED_LAYOUT_SPACING)
            self._preview_title_label.show()
            self._workspace_notes.show()
            self._window_toolbar.show()
            self._window.statusBar().show()
            self._suspend_dock_sync = True
            self._controls_dock.setVisible(self._controls_dock_requested)
            self._suspend_dock_sync = False
            self._layout_fullscreen_surface()
            notice = "Windowed view active."
        self._render_latest_preview()
        self._set_status(self._preview_state, notice=notice)
        self._persist_workspace_state()

    def _toggle_fullscreen(self, checked: bool | None = None) -> None:
        """Toggle the main window between windowed and fullscreen states."""

        if checked is None:
            checked = not self._is_fullscreen
        self._set_fullscreen(bool(checked))

    def _handle_controls_dock_visibility_changed(self, visible: bool) -> None:
        """Keep status and action state in sync with dock visibility."""

        if not self._suspend_dock_sync:
            self._controls_dock_requested = bool(visible)
        was_blocked = self._toggle_controls_action.blockSignals(True)
        self._toggle_controls_action.setChecked(bool(visible))
        self._toggle_controls_action.blockSignals(was_blocked)
        notice = "Controls dock open." if visible else "Controls dock closed."
        self._set_status(self._preview_state, notice=notice)
        self._render_latest_preview()
        self._layout_fullscreen_surface()
        self._persist_workspace_state()

    def _toggle_controls_dock(self, checked: bool | None = None) -> None:
        """Open or close the dedicated controls dock."""

        if checked is None:
            checked = not self._controls_dock.isVisible()
        self._controls_dock.setVisible(bool(checked))

    def _refresh_cameras_action(self, _checked=False) -> None:
        """Refresh cameras from the native menu and toolbar actions."""

        self.refresh_cameras(auto_open=True)

    def _persist_output_directories(self) -> None:
        """Store the current output directories for the next launch."""

        self._settings.setValue(
            SETTINGS_IMAGE_DIRECTORY_KEY,
            str(self._image_directory),
        )
        self._settings.setValue(
            SETTINGS_VIDEO_DIRECTORY_KEY,
            str(self._video_directory),
        )

    def _open_selected_camera_action(self, _checked=False) -> None:
        """Open the selected camera from a native Qt action callback."""

        self.open_selected_camera()

    def _capture_still_action(self, _checked=False) -> None:
        """Save one framed still image to the configured output folder."""

        if self._latest_frame is None:
            self._set_status(
                self._preview_state,
                notice="Wait for a live preview frame before saving a still.",
            )
            self._record_diagnostic_event(
                "Wait for a live preview frame before saving a still."
            )
            return
        output_path = _next_available_output_path(
            _default_still_output_path(self._image_directory)
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        target_width, target_height = self._preview_target_size()
        image = _capture_image_from_frame(
            self._latest_frame,
            framing_mode=self._capture_framing_mode,
            target_width=target_width,
            target_height=target_height,
            qt_gui=self._qt_gui,
        )
        if not image.save(
            str(output_path), _still_format_for_path(output_path)
        ):
            self._set_status(
                self._preview_state,
                notice="Still capture failed.",
            )
            self._record_diagnostic_event("Still capture failed.")
            return
        self._image_directory = output_path.parent
        self._persist_output_directories()
        self._set_status(
            self._preview_state,
            notice=f"Saved still to {output_path.name}.",
        )

    def _toggle_recording_action(self, _checked=False) -> None:
        """Start or stop native Qt recording for the active session."""

        if self._session is None:
            self._set_status(
                self._preview_state,
                notice="Open a camera before starting a recording.",
            )
            self._record_diagnostic_event(
                "Open a camera before starting a recording."
            )
            return
        if self._session.recording_state == "recording":
            output_path = self._session.stop_recording()
            self._refresh_recording_state()
            notice = "Stopped recording."
            if output_path is not None:
                notice = f"Stopped recording to {output_path.name}."
            self._set_status(self._preview_state, notice=notice)
            return
        output_path = self._select_output_path(
            title="Start Recording",
            initial_path=_default_recording_output_path(
                self._video_directory,
                suffix=_preferred_recording_output_suffix(self._qt_multimedia),
            ),
            filter_text=build_recording_file_filter(self._qt_multimedia),
        )
        if output_path is None:
            self._set_status(
                self._preview_state,
                notice="Recording canceled.",
            )
            self._record_diagnostic_event("Recording canceled.")
            return
        if self._latest_frame is None:
            self._set_status(
                self._preview_state,
                notice="Wait for a live preview frame before recording.",
            )
            self._record_diagnostic_event(
                "Wait for a live preview frame before recording."
            )
            return
        target_width, target_height = self._preview_target_size()
        crop_plan = _recording_crop_plan_from_frame(
            self._latest_frame,
            framing_mode=self._capture_framing_mode,
            target_width=target_width,
            target_height=target_height,
        )
        try:
            recorded_path = self._session.start_recording(
                output_path,
                crop_plan=crop_plan,
            )
        except CameraOutputError as exc:
            self._set_status(self._preview_state, notice=str(exc))
            self._record_diagnostic_event(str(exc))
            return
        self._video_directory = recorded_path.parent
        self._persist_output_directories()
        self._recording_state = "recording 00:00"
        self._set_status(
            self._preview_state,
            notice=f"Recording to {recorded_path.name}.",
        )

    def _open_preferences(self, _checked=False) -> None:
        """Open a native Qt dialog for session-level shell preferences."""

        QtWidgets = self._qt_widgets

        dialog = QtWidgets.QDialog(self._window)
        dialog.setWindowTitle("Preferences")
        dialog.resize(660, 560)
        layout = QtWidgets.QVBoxLayout(dialog)
        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        preview_combo = QtWidgets.QComboBox(dialog)
        capture_combo = QtWidgets.QComboBox(dialog)
        for mode in PREVIEW_FRAMING_MODES:
            label = PREVIEW_FRAMING_LABELS[mode]
            preview_combo.addItem(label, mode)
            capture_combo.addItem(label, mode)
        preview_combo.setCurrentIndex(
            preview_combo.findData(self._preview_framing_mode)
        )
        capture_combo.setCurrentIndex(
            capture_combo.findData(self._capture_framing_mode)
        )

        image_row = QtWidgets.QHBoxLayout()
        image_field = QtWidgets.QLineEdit(str(self._image_directory), dialog)
        image_browse = QtWidgets.QPushButton("Browse", dialog)
        image_row.addWidget(image_field, 1)
        image_row.addWidget(image_browse)

        video_row = QtWidgets.QHBoxLayout()
        video_field = QtWidgets.QLineEdit(str(self._video_directory), dialog)
        video_browse = QtWidgets.QPushButton("Browse", dialog)
        video_row.addWidget(video_field, 1)
        video_row.addWidget(video_browse)

        # Reuse one native folder chooser for both output-directory fields.
        def choose_directory(field) -> None:
            selected = QtWidgets.QFileDialog.getExistingDirectory(
                dialog,
                "Choose Folder",
                field.text(),
            )
            if selected:
                field.setText(selected)

        image_browse.clicked.connect(lambda: choose_directory(image_field))
        video_browse.clicked.connect(lambda: choose_directory(video_field))

        image_widget = QtWidgets.QWidget(dialog)
        image_widget.setLayout(image_row)
        video_widget = QtWidgets.QWidget(dialog)
        video_widget.setLayout(video_row)
        form.addRow("Preview framing", preview_combo)
        form.addRow("Capture framing", capture_combo)
        form.addRow("Image folder", image_widget)
        form.addRow("Video folder", video_widget)
        layout.addLayout(form)

        preset_combo = QtWidgets.QComboBox(dialog)
        preset_combo.setEditable(True)
        preset_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        preset_combo.setMinimumContentsLength(24)
        preset_line_edit = preset_combo.lineEdit()
        if preset_line_edit is not None:
            preset_line_edit.setPlaceholderText("Choose or name a preset")

        # Keep preset storage and recall in the same dialog as the other
        # session-level preferences so microscope setups can be captured
        # without opening another surface.
        def refresh_preset_combo(selected_name: str | None = None) -> None:
            """Rebuild the preset picker from the stored preset map."""

            if selected_name is None:
                current_name = _settings_text(
                    preset_combo.currentText(),
                    default="",
                )
            else:
                current_name = _settings_text(selected_name, default="")
            was_blocked = preset_combo.blockSignals(True)
            preset_combo.clear()
            for preset_name in sorted(self._named_presets):
                preset_combo.addItem(preset_name, preset_name)
            if current_name:
                index = preset_combo.findData(current_name)
                if index >= 0:
                    preset_combo.setCurrentIndex(index)
                else:
                    preset_combo.setEditText(current_name)
            else:
                preset_combo.setEditText("")
            preset_combo.blockSignals(was_blocked)

        named_presets_box = QtWidgets.QGroupBox("Named Presets", dialog)
        named_presets_layout = QtWidgets.QVBoxLayout(named_presets_box)
        named_presets_layout.setContentsMargins(12, 12, 12, 12)
        named_presets_layout.setSpacing(8)
        presets_note = QtWidgets.QLabel(
            "Choose an existing preset or type a new name, then save or "
            "apply it.",
            named_presets_box,
        )
        presets_note.setWordWrap(True)
        named_presets_layout.addWidget(presets_note)
        named_presets_form = QtWidgets.QFormLayout()
        named_presets_form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        named_presets_form.addRow("Preset name", preset_combo)
        named_presets_layout.addLayout(named_presets_form)
        preset_buttons_row = QtWidgets.QHBoxLayout()
        save_preset_button = QtWidgets.QPushButton(
            "Save Current",
            named_presets_box,
        )
        apply_preset_button = QtWidgets.QPushButton(
            "Apply Selected",
            named_presets_box,
        )
        preset_buttons_row.addWidget(save_preset_button)
        preset_buttons_row.addWidget(apply_preset_button)
        preset_buttons_row.addStretch(1)
        preset_buttons_widget = QtWidgets.QWidget(named_presets_box)
        preset_buttons_widget.setLayout(preset_buttons_row)
        named_presets_layout.addWidget(preset_buttons_widget)
        layout.addWidget(named_presets_box)
        refresh_preset_combo(self._current_preset_name)

        default_widgets: dict[str, object] = {}
        defaults_box = QtWidgets.QGroupBox("Control Defaults", dialog)
        defaults_layout = QtWidgets.QVBoxLayout(defaults_box)
        defaults_layout.setContentsMargins(12, 12, 12, 12)
        defaults_layout.setSpacing(8)
        editable_controls = [
            control
            for control in self._active_controls
            if control.kind in {"numeric", "boolean", "enum"}
            and control.value is not None
        ]
        if editable_controls:
            for section_name, section_controls in _group_controls_for_surface(
                tuple(editable_controls)
            ):
                section_box = QtWidgets.QGroupBox(section_name, defaults_box)
                section_layout = QtWidgets.QFormLayout(section_box)
                section_layout.setFieldGrowthPolicy(
                    QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
                )
                for control in section_controls:
                    default_value = self._settings.value(
                        _control_default_setting_key(control.control_id)
                    )
                    if default_value is None:
                        default_value = BUILTIN_CONTROL_DEFAULT_VALUES.get(
                            control.control_id,
                            control.value,
                        )
                    if control.kind == "boolean":
                        widget = QtWidgets.QCheckBox(section_box)
                        widget.setChecked(bool(default_value))
                    elif control.kind == "enum":
                        widget = QtWidgets.QComboBox(section_box)
                        for choice in control.choices:
                            widget.addItem(choice.label, choice.value)
                        if default_value is not None:
                            index = widget.findData(str(default_value))
                            if index >= 0:
                                widget.setCurrentIndex(index)
                    else:
                        widget = QtWidgets.QLineEdit(
                            str(
                                default_value
                                if default_value is not None
                                else ""
                            ),
                            section_box,
                        )
                    default_widgets[control.control_id] = widget
                    section_layout.addRow(control.label, widget)
                defaults_layout.addWidget(section_box)
        else:
            defaults_layout.addWidget(
                QtWidgets.QLabel(
                    "Open a camera to edit control defaults.", defaults_box
                )
            )
        layout.addWidget(defaults_box)

        shortcut_widgets: dict[str, object] = {}
        shortcuts_box = QtWidgets.QGroupBox("Keyboard Shortcuts", dialog)
        shortcuts_layout = QtWidgets.QFormLayout(shortcuts_box)
        shortcuts_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        for (
            action_id,
            label,
            default_text,
            _action_attr,
        ) in self._shortcut_actions:
            action = self._shortcut_action_for_id(action_id)
            current_text = (
                action.shortcut().toString()
                if action is not None
                else default_text
            )
            widget = QtWidgets.QLineEdit(current_text, shortcuts_box)
            shortcut_widgets[action_id] = widget
            shortcuts_layout.addRow(label, widget)
        layout.addWidget(shortcuts_box)

        def save_named_preset() -> None:
            """Save the current workspace snapshot under one preset name."""

            preset_name = _settings_text(
                preset_combo.currentText(), default=""
            )
            if not preset_name:
                QtWidgets.QMessageBox.warning(
                    dialog,
                    "Invalid preset",
                    "Preset names cannot be blank.",
                )
                return
            if not self._save_named_preset(preset_name):
                QtWidgets.QMessageBox.warning(
                    dialog,
                    "Invalid preset",
                    "Preset names cannot be blank.",
                )
                return
            refresh_preset_combo(preset_name)
            self._set_status(
                self._preview_state,
                notice=f"Saved preset {preset_name}.",
            )

        def apply_named_preset() -> None:
            """Recall one stored preset into the live shell."""

            preset_name = _settings_text(
                preset_combo.currentText(), default=""
            )
            if not preset_name:
                QtWidgets.QMessageBox.warning(
                    dialog,
                    "Invalid preset",
                    "Choose or name a preset before applying it.",
                )
                return
            if not self._apply_named_preset(preset_name):
                QtWidgets.QMessageBox.warning(
                    dialog,
                    "Missing preset",
                    "Save the named preset before applying it.",
                )
                self._record_diagnostic_event(
                    f"Missing preset: {preset_name}."
                )
                return
            refresh_preset_combo(preset_name)

        save_preset_button.clicked.connect(save_named_preset)
        apply_preset_button.clicked.connect(apply_named_preset)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )

        def accept_dialog() -> None:
            """Validate and persist preferences before closing."""

            for control in editable_controls:
                widget = default_widgets[control.control_id]
                value = _control_value_for_storage(
                    control,
                    widget,
                    qt_gui=self._qt_gui,
                )
                if control.kind == "numeric" and value is None:
                    QtWidgets.QMessageBox.warning(
                        dialog,
                        "Invalid default",
                        f"{control.label} needs a valid numeric value.",
                    )
                    return
                self._settings.setValue(
                    _control_default_setting_key(control.control_id),
                    value,
                )

            shortcut_values: dict[str, str] = {}
            for action_id, widget in shortcut_widgets.items():
                shortcut_text = _shortcut_key_text(widget.text())
                if not shortcut_text:
                    QtWidgets.QMessageBox.warning(
                        dialog,
                        "Invalid shortcut",
                        "Shortcut entries cannot be blank.",
                    )
                    return
                shortcut_values[action_id] = shortcut_text
            conflict = _shortcut_conflict_label(shortcut_values)
            if conflict is not None:
                QtWidgets.QMessageBox.warning(
                    dialog,
                    "Shortcut conflict",
                    conflict,
                )
                return
            self._apply_shortcut_texts(shortcut_values)
            self._shortcut_text_by_action = shortcut_values
            self._persist_workspace_state()
            if self._selected_descriptor() is not None:
                self._apply_persisted_control_state()
            dialog.accept()

        buttons.accepted.connect(accept_dialog)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if int(getattr(dialog, "exec")()) != int(
            QtWidgets.QDialog.DialogCode.Accepted
        ):
            self._set_status(
                self._preview_state,
                notice="Preferences closed without changes.",
            )
            return

        self._image_directory = Path(image_field.text()).expanduser()
        self._video_directory = Path(video_field.text()).expanduser()
        self._persist_output_directories()
        self._set_preview_framing_mode(str(preview_combo.currentData()))
        self._set_capture_framing_mode(str(capture_combo.currentData()))
        self._set_status(
            self._preview_state,
            notice="Applied session preferences.",
        )

    def _open_diagnostics(self, _checked=False) -> None:
        """Open a native Qt diagnostics view for the current shell state."""

        QtWidgets = self._qt_widgets

        dialog = QtWidgets.QDialog(self._window)
        dialog.setWindowTitle("Diagnostics")
        dialog.resize(760, 520)
        layout = QtWidgets.QVBoxLayout(dialog)

        tab_widget = QtWidgets.QTabWidget(dialog)

        def add_text_tab(title: str, lines: tuple[str, ...]):
            """Add one read-only text tab to the diagnostics surface."""

            editor = QtWidgets.QPlainTextEdit(dialog)
            editor.setReadOnly(True)
            editor.setPlainText("\n".join(lines))
            tab_widget.addTab(editor, title)
            return editor

        add_text_tab("Runtime", self._current_diagnostics_lines())
        add_text_tab("Recent Notices", self._diagnostic_log_lines())
        add_text_tab("Exit Checks", self._current_exit_check_lines())
        layout.addWidget(tab_widget, 1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close,
            parent=dialog,
        )
        copy_button = buttons.addButton(
            "Copy",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )

        def copy_current_report() -> None:
            """Copy the currently visible diagnostics tab."""

            widget = tab_widget.currentWidget()
            if widget is None or not hasattr(widget, "toPlainText"):
                return
            self._application.clipboard().setText(widget.toPlainText())

        copy_button.clicked.connect(copy_current_report)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        getattr(dialog, "exec")()
        self._set_status(
            self._preview_state,
            notice="Viewed diagnostics and exit checks.",
        )

    def _copy_status_summary(self, _checked=False) -> None:
        """Copy the visible status summary to the clipboard."""

        self._application.clipboard().setText(self._status_label.text())
        self._set_status(
            self._preview_state,
            notice="Copied the status summary to the clipboard.",
        )

    def _show_about(self, _checked=False) -> None:
        """Show a short about dialog through the native Qt shell."""

        self._qt_widgets.QMessageBox.information(
            self._window,
            APP_NAME,
            (
                f"{APP_NAME} uses {GUI_BASELINE} with "
                f"{self._backend.backend_name} preview."
            ),
        )
        self._set_status(
            self._preview_state,
            notice=(
                f"{APP_NAME} uses {GUI_BASELINE} with "
                f"{self._backend.backend_name} preview."
            ),
        )

    def _handle_quit(self) -> None:
        """Shut down preview resources before the app session closes."""

        if self._closed:
            return
        self._closed = True
        self._persist_workspace_state()
        self.close_session()

    def run(self) -> int:
        """Finish the application bootstrap and start the Qt event loop."""

        self._preview_timer = self._qt_core.QTimer(self._window)
        if hasattr(self._preview_timer, "setTimerType") and hasattr(
            self._qt_core.Qt, "TimerType"
        ):
            self._preview_timer.setTimerType(
                self._qt_core.Qt.TimerType.PreciseTimer
            )
        self._preview_timer.setInterval(self.refresh_interval_milliseconds)
        self._preview_timer.timeout.connect(self._poll_preview_frame)
        self._preview_timer.start()
        self._fit_action.setChecked(True)
        self._sync_action_states()
        self.refresh_cameras(auto_open=True)
        self._window.show()
        if self._is_fullscreen:
            self._set_fullscreen(True)
        exec_method = getattr(self._application, "exec")
        return int(exec_method())


def launch_main_window() -> int:
    """Launch the Qt Widgets workspace."""

    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ModuleNotFoundError as exc:
        raise MissingGuiDependencyError(
            "Install the package runtime dependencies before launching the "
            "GUI shell."
        ) from exc

    application = QtWidgets.QApplication.instance()
    if application is None:
        application = QtWidgets.QApplication(sys.argv)
    preview_application = PreviewApplication(
        QtCore,
        QtGui,
        QtWidgets,
        application,
    )
    return preview_application.run()
