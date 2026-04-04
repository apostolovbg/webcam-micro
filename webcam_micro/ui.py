"""Qt Widgets shell assembly for the PySide6 migration foundation."""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

from webcam_micro import APP_NAME, GUI_BASELINE, SHELL_TITLE
from webcam_micro.camera import (
    CameraControl,
    CameraControlApplyError,
    CameraDescriptor,
    MissingCameraDependencyError,
    NullCameraBackend,
    PreviewFrame,
    QtCameraBackend,
    build_backend_plan,
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
            "surface close to the preview workspace, and camera controls "
            "live in a toggleable dock.",
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
            "Recording: {recording} | {notice}"
        ),
        copyright_notice="© Apostol Apostolov",
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

    refresh_interval_milliseconds = 50

    def __init__(self, qt_core, qt_gui, qt_widgets, qt_application) -> None:
        """Build the Qt shell and initialize runtime state."""

        self._qt_core = qt_core
        self._qt_gui = qt_gui
        self._qt_widgets = qt_widgets
        self._application = qt_application
        self._spec = build_shell_spec()
        self._backend = self._build_backend()
        self._session = None
        self._cameras: tuple[CameraDescriptor, ...] = ()
        self._selected_camera_id: str | None = None
        self._active_controls: tuple[CameraControl, ...] = ()
        self._controls_by_id: dict[str, CameraControl] = {}
        self._latest_frame: PreviewFrame | None = None
        self._last_frame_number = -1
        self._closed = False
        self._is_fullscreen = False
        self._fullscreen_surface_expanded = True
        self._suspend_dock_sync = False
        self._controls_dock_requested = True
        self._preview_state = "idle"
        self._preview_framing_mode = "fit"
        self._capture_framing_mode = "fit"
        self._recording_state = "not ready"
        self._status_notice = "Workspace ready."

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
        self._fit_action = None
        self._fill_action = None
        self._crop_action = None
        self._fullscreen_action = None
        self._window_toolbar = None
        self._fullscreen_surface = None
        self._fullscreen_surface_layout = None
        self._escape_shortcut = None
        self._preview_timer = None

        self._build_window()

    def _build_backend(self):
        """Return the active preview backend or a null fallback."""

        try:
            return QtCameraBackend()
        except MissingCameraDependencyError:
            return NullCameraBackend()

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
        self._refresh_action.triggered.connect(self._refresh_cameras_action)

        self._open_action = QtGui.QAction("Open", self._window)
        self._open_action.triggered.connect(self._open_selected_camera_action)

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
        self._still_action.triggered.connect(self._capture_still_action)

        self._record_action = QtGui.QAction("Record", self._window)
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

        self._diagnostics_action = QtGui.QAction("Diagnostics", self._window)
        self._diagnostics_action.triggered.connect(self._open_diagnostics)

        self._copy_status_action = QtGui.QAction(
            "Copy Status Summary", self._window
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
        controls_by_kind: dict[str, list[CameraControl]] = {
            "numeric": [],
            "boolean": [],
            "enum": [],
            "read_only": [],
            "action": [],
        }
        for control in self._active_controls:
            controls_by_kind.setdefault(control.kind, []).append(control)
        if not self._active_controls:
            self._controls_body_layout.addWidget(
                self._qt_widgets.QLabel(
                    "No camera controls are currently available for the "
                    "selected camera/backend."
                )
            )
            self._controls_body_layout.addStretch(1)
            return

        sections = (
            ("Numeric Controls", "numeric", self._build_numeric_control),
            ("Toggle Controls", "boolean", self._build_boolean_control),
            ("Enumerated Controls", "enum", self._build_enum_control),
            ("Read-Only Details", "read_only", self._build_read_only_control),
            ("Actions", "action", self._build_action_control),
        )
        for heading, kind, builder in sections:
            controls = controls_by_kind[kind]
            if not controls:
                continue
            self._controls_body_layout.addWidget(
                self._controls_section_heading(heading)
            )
            for control in controls:
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
            return
        message = f"Updated {control.label}."
        self._set_controls_notice(message)
        if status_notice:
            self._set_status(self._preview_state, notice=message)
        if refresh_surface:
            self._refresh_control_surface(notice=message)

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
                recording=status.recording_state,
                notice=status.notice,
            )
        )
        self._sync_controls_summary()

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
            return

        self._selected_camera_id = self._cameras[0].stable_id
        was_blocked = self._camera_combo.blockSignals(True)
        self._camera_combo.setCurrentIndex(0)
        self._camera_combo.blockSignals(was_blocked)
        self._set_preview_message("Opening camera...")
        self._refresh_control_surface(notice="Camera list refreshed.")
        self._set_status("camera ready", notice="Camera list refreshed.")
        if auto_open:
            self.open_selected_camera()

    def _handle_camera_index_changed(self, index: int) -> None:
        """Handle a camera selection change from the combo box."""

        if index < 0 or index >= len(self._cameras):
            return
        self._selected_camera_id = self._cameras[index].stable_id
        self.open_selected_camera()

    def open_selected_camera(self) -> None:
        """Open the chosen camera and start preview updates."""

        descriptor = self._selected_descriptor()
        if descriptor is None:
            self._set_preview_message("No camera selected.")
            self._refresh_control_surface(notice="Choose a camera first.")
            self._set_status("no selection", notice="Choose a camera first.")
            return
        self.close_session()
        try:
            self._session = self._backend.open_session(descriptor)
        except RuntimeError as exc:
            self._set_preview_message(str(exc))
            self._refresh_control_surface(notice=str(exc))
            self._set_status("open failed", notice="Camera open failed.")
            return
        self._set_preview_message("Waiting for live preview frames...")
        self._refresh_control_surface(notice="Loaded camera controls.")
        self._set_status("opening", notice="Opening selected camera.")

    def _poll_preview_frame(self) -> None:
        """Poll the newest frame and refresh the preview without lagging."""

        if self._closed or self._session is None:
            return
        failure_reason = self._session.failure_reason
        if failure_reason:
            self._set_preview_message(failure_reason)
            self._set_status(
                "preview failed",
                notice="Preview failed; see on-screen error.",
            )
            return
        frame = self._session.get_latest_frame()
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

    def _toggle_controls_dock(self, checked: bool | None = None) -> None:
        """Open or close the dedicated controls dock."""

        if checked is None:
            checked = not self._controls_dock.isVisible()
        self._controls_dock.setVisible(bool(checked))

    def _refresh_cameras_action(self, _checked=False) -> None:
        """Refresh cameras from the native menu and toolbar actions."""

        self.refresh_cameras(auto_open=True)

    def _open_selected_camera_action(self, _checked=False) -> None:
        """Open the selected camera from a native Qt action callback."""

        self.open_selected_camera()

    def _capture_still_action(self, _checked=False) -> None:
        """Announce the staged still-capture placeholder."""

        self._set_status(
            self._preview_state,
            notice="Still capture lands after the Qt foundation slice.",
        )

    def _toggle_recording_action(self, _checked=False) -> None:
        """Announce the staged recording placeholder."""

        self._set_status(
            self._preview_state,
            notice="Recording lands after the Qt foundation slice.",
        )

    def _open_preferences(self, _checked=False) -> None:
        """Announce the staged preferences placeholder."""

        self._set_status(
            self._preview_state,
            notice="Preferences land after the Qt foundation slice.",
        )

    def _open_diagnostics(self, _checked=False) -> None:
        """Announce the staged diagnostics placeholder."""

        self._set_status(
            self._preview_state,
            notice="Diagnostics land after the Qt foundation slice.",
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
        self.close_session()

    def run(self) -> int:
        """Finish the application bootstrap and start the Qt event loop."""

        self._preview_timer = self._qt_core.QTimer(self._window)
        self._preview_timer.setInterval(self.refresh_interval_milliseconds)
        self._preview_timer.timeout.connect(self._poll_preview_frame)
        self._preview_timer.start()
        self._fit_action.setChecked(True)
        self.refresh_cameras(auto_open=True)
        self._window.show()
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
