"""GUI shell assembly for the Stage 4 controls-aware workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image

from webcam_micro import APP_NAME, GUI_BASELINE, SHELL_TITLE
from webcam_micro.camera import (
    CameraControl,
    CameraControlApplyError,
    CameraDescriptor,
    FfmpegCameraBackend,
    MissingCameraDependencyError,
    NullCameraBackend,
    build_backend_plan,
)

if TYPE_CHECKING:
    import tkinter as tkinter_module


class MissingGuiDependencyError(RuntimeError):
    """Raised when the GUI dependency set is not installed."""


@dataclass(frozen=True)
class ShellSpec:
    """Describe the working shape of the Stage 4 main window."""

    title: str
    theme_name: str
    hero_title: str
    hero_body: tuple[str, ...]
    menu_sections: tuple[str, ...]
    toolbar_actions: tuple[str, ...]
    controls_window_title: str
    status_template: str
    copyright_notice: str


def build_shell_spec() -> ShellSpec:
    """Return the Stage 4 controls-aware shell description."""

    backend_plan = build_backend_plan()
    return ShellSpec(
        title=SHELL_TITLE,
        theme_name="litera",
        hero_title=APP_NAME,
        hero_body=(
            "Preview-first microscope camera prototype workspace.",
            f"GUI baseline: {GUI_BASELINE}",
            "Backend baseline: " f"{backend_plan.first_device_backend_target}",
            "Controls live in a separate window to protect preview space.",
        ),
        menu_sections=(
            "File",
            "Edit",
            "View",
            "Camera",
            "Capture",
            "Tools",
            "Help",
        ),
        toolbar_actions=(
            "Controls",
            "Refresh",
            "Open",
            "Still",
            "Record",
            "Fullscreen",
            "Preferences",
        ),
        controls_window_title="Camera Controls",
        status_template=(
            "Backend: {backend} | Camera: {camera} | Source: {source} | "
            "Framing: {framing} | Controls: {controls} | "
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
    controls_window_state: str
    recording_state: str
    notice: str


def build_runtime_status(
    backend_name: str,
    camera_name: str,
    preview_state: str,
    source_mode: str,
    framing_mode: str,
    controls_window_state: str,
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
        controls_window_state=controls_window_state,
        recording_state=recording_state,
        notice=notice,
    )


def format_numeric_control_value(
    value: float,
    step: float | None,
) -> str:
    """Return a stable numeric string for sliders, labels, and spinboxes."""

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
    """Parse one numeric entry value and reject invalid input as `None`."""

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


class PreviewApplication:
    """Manage camera discovery, sessions, preview, and control updates."""

    refresh_interval_ms = 15
    control_apply_delay_ms = 45

    def __init__(self, ttkb_module) -> None:
        """Build the Stage 4 shell and initialize runtime state."""

        self._ttkb = ttkb_module
        self._spec = build_shell_spec()
        self._window = ttkb_module.Window(themename=self._spec.theme_name)
        self._window.title(self._spec.title)
        self._window.geometry("1080x720")
        self._window.minsize(800, 560)
        self._window.protocol("WM_DELETE_WINDOW", self._handle_close)

        self._backend = self._build_backend()
        self._session = None
        self._cameras: tuple[CameraDescriptor, ...] = ()
        self._selected_camera_index: int | None = None
        self._active_controls: tuple[CameraControl, ...] = ()
        self._controls_by_id: dict[str, CameraControl] = {}
        self._preview_image = None
        self._last_frame_number = -1
        self._closed = False
        self._is_fullscreen = False
        self._controls_window: tkinter_module.Toplevel | None = None
        self._controls_content_frame = None
        self._preview_state = "idle"
        self._framing_mode = "fit"
        self._recording_state = "not ready"
        self._status_notice = "Workspace ready."
        self._pending_control_apply_ids: dict[str, str] = {}
        self._numeric_scale_vars: dict[str, object] = {}
        self._numeric_entry_vars: dict[str, object] = {}
        self._boolean_vars: dict[str, object] = {}
        self._enum_vars: dict[str, object] = {}
        self._enum_label_maps: dict[str, dict[str, str]] = {}

        self._camera_var = ttkb_module.StringVar(value="")
        self._status_var = ttkb_module.StringVar(value="")
        self._controls_summary_var = ttkb_module.StringVar(value="")
        self._controls_notice_var = ttkb_module.StringVar(
            value="Open a camera to inspect the active control surface."
        )

        self._build_menu_bar()
        self._build_layout()
        self.refresh_cameras(auto_open=True)
        self._window.after(self.refresh_interval_ms, self._tick_preview)

    def _build_backend(self):
        """Return the active preview backend or a null fallback."""

        try:
            return FfmpegCameraBackend()
        except MissingCameraDependencyError:
            return NullCameraBackend()

    def _build_menu_bar(self) -> None:
        """Create the governed menu structure for the main window."""

        import tkinter as tkinter_module

        menu_bar = tkinter_module.Menu(self._window)

        file_menu = tkinter_module.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Exit", command=self._handle_close)
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tkinter_module.Menu(menu_bar, tearoff=False)
        edit_menu.add_command(
            label="Preferences",
            command=self._open_preferences,
        )
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tkinter_module.Menu(menu_bar, tearoff=False)
        view_menu.add_command(
            label="Toggle Controls Window",
            command=self._toggle_controls_window,
        )
        view_menu.add_command(
            label="Toggle Fullscreen",
            command=self._toggle_fullscreen,
        )
        menu_bar.add_cascade(label="View", menu=view_menu)

        camera_menu = tkinter_module.Menu(menu_bar, tearoff=False)
        camera_menu.add_command(
            label="Refresh Cameras",
            command=self._refresh_cameras_action,
        )
        camera_menu.add_command(
            label="Open Selected Camera",
            command=self.open_selected_camera,
        )
        camera_menu.add_command(
            label="Close Camera",
            command=self._close_camera_action,
        )
        menu_bar.add_cascade(label="Camera", menu=camera_menu)

        capture_menu = tkinter_module.Menu(menu_bar, tearoff=False)
        capture_menu.add_command(
            label="Capture Still",
            command=self._capture_still_action,
        )
        capture_menu.add_command(
            label="Toggle Recording",
            command=self._toggle_recording_action,
        )
        menu_bar.add_cascade(label="Capture", menu=capture_menu)

        tools_menu = tkinter_module.Menu(menu_bar, tearoff=False)
        tools_menu.add_command(
            label="Diagnostics",
            command=self._open_diagnostics,
        )
        menu_bar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tkinter_module.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="About", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self._window.configure(menu=menu_bar)
        self._menu_bar = menu_bar

    def _build_layout(self) -> None:
        """Build the preview-first Stage 4 shell."""

        root_frame = self._ttkb.Frame(self._window, padding=16)
        root_frame.pack(fill="both", expand=True)

        toolbar = self._ttkb.Frame(root_frame)
        toolbar.pack(fill="x", pady=(0, 12))

        title_label = self._ttkb.Label(
            toolbar,
            text=self._spec.hero_title,
            font=("TkDefaultFont", 18, "bold"),
        )
        title_label.pack(side="left")

        controls_button = self._ttkb.Button(
            toolbar,
            text="Controls",
            command=self._toggle_controls_window,
            bootstyle="secondary",
        )
        controls_button.pack(side="left", padx=(12, 0))

        self._camera_combo = self._ttkb.Combobox(
            toolbar,
            textvariable=self._camera_var,
            state="readonly",
            width=32,
        )
        self._camera_combo.pack(side="left", padx=(12, 0))
        self._camera_combo.bind(
            "<<ComboboxSelected>>",
            self._on_camera_selected,
        )

        refresh_button = self._ttkb.Button(
            toolbar,
            text="Refresh",
            command=self._refresh_cameras_action,
            bootstyle="secondary",
        )
        refresh_button.pack(side="left", padx=(12, 0))

        open_button = self._ttkb.Button(
            toolbar,
            text="Open",
            command=self.open_selected_camera,
            bootstyle="primary",
        )
        open_button.pack(side="left", padx=(12, 0))

        still_button = self._ttkb.Button(
            toolbar,
            text="Still",
            command=self._capture_still_action,
            bootstyle="secondary",
        )
        still_button.pack(side="left", padx=(12, 0))

        record_button = self._ttkb.Button(
            toolbar,
            text="Record",
            command=self._toggle_recording_action,
            bootstyle="secondary",
        )
        record_button.pack(side="left", padx=(12, 0))

        fullscreen_button = self._ttkb.Button(
            toolbar,
            text="Fullscreen",
            command=self._toggle_fullscreen,
            bootstyle="secondary",
        )
        fullscreen_button.pack(side="left", padx=(12, 0))

        preferences_button = self._ttkb.Button(
            toolbar,
            text="Preferences",
            command=self._open_preferences,
            bootstyle="secondary",
        )
        preferences_button.pack(side="left", padx=(12, 0))

        spacer = self._ttkb.Frame(toolbar)
        spacer.pack(side="left", fill="x", expand=True)

        signature_label = self._ttkb.Label(
            toolbar,
            text=self._spec.copyright_notice,
        )
        signature_label.pack(side="left")

        preview_frame = self._ttkb.Labelframe(
            root_frame,
            text="Live Preview",
            padding=12,
        )
        preview_frame.pack(fill="both", expand=True)

        self._preview_label = self._ttkb.Label(
            preview_frame,
            text="Refreshing cameras...",
            anchor="center",
            justify="center",
        )
        self._preview_label.pack(fill="both", expand=True)

        workspace_notes = self._ttkb.Label(
            root_frame,
            text=" ".join(self._spec.hero_body),
            justify="left",
            wraplength=980,
        )
        workspace_notes.pack(anchor="w", pady=(12, 0))

        status_bar = self._ttkb.Label(
            self._window,
            textvariable=self._status_var,
            anchor="w",
            justify="left",
            wraplength=1160,
            padding=(12, 6),
        )
        status_bar.pack(fill="x", side="bottom")
        self._set_status("idle", notice="Workspace ready.")

    def _selected_descriptor(self) -> CameraDescriptor | None:
        """Return the currently selected camera descriptor, if any."""

        if self._selected_camera_index is None:
            return None
        if 0 <= self._selected_camera_index < len(self._cameras):
            return self._cameras[self._selected_camera_index]
        return None

    def _build_controls_summary(self) -> str:
        """Return the visible summary shown in the controls window."""

        control_count = len(self._active_controls)
        lines = [
            f"Backend: {self._backend.backend_name}",
            f"Camera: {self._selected_camera_name()}",
            f"Preview: {self._preview_state}",
            f"Source mode: {self._source_mode_label()}",
            f"Framing mode: {self._framing_mode}",
            f"Controls surfaced: {control_count}",
        ]
        if control_count:
            kind_counts: dict[str, int] = {}
            for control in self._active_controls:
                kind_counts[control.kind] = (
                    kind_counts.get(control.kind, 0) + 1
                )
            summary_bits = [
                f"{kind}={kind_counts[kind]}"
                for kind in (
                    "numeric",
                    "boolean",
                    "enum",
                    "read_only",
                    "action",
                )
                if kind in kind_counts
            ]
            lines.append("Kinds: " + ", ".join(summary_bits))
        else:
            lines.append(
                "The current camera/backend combination does not expose "
                "controls yet."
            )
        return "\n".join(lines)

    def _set_controls_notice(self, message: str) -> None:
        """Update the controls-window notice text."""

        self._controls_notice_var.set(message)

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
            self._render_controls()
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
        self._render_controls()

    def _ensure_controls_window(self) -> None:
        """Create the separate controls window when first requested."""

        import tkinter as tkinter_module

        if self._controls_window is not None:
            return
        controls_window = tkinter_module.Toplevel(self._window)
        controls_window.title(self._spec.controls_window_title)
        controls_window.geometry("560x680")
        controls_window.minsize(420, 420)
        controls_window.protocol(
            "WM_DELETE_WINDOW",
            self._handle_controls_window_close,
        )

        root_frame = self._ttkb.Frame(controls_window, padding=16)
        root_frame.pack(fill="both", expand=True)

        title_label = self._ttkb.Label(
            root_frame,
            text=self._spec.controls_window_title,
            font=("TkDefaultFont", 16, "bold"),
        )
        title_label.pack(anchor="w")

        summary_label = self._ttkb.Label(
            root_frame,
            textvariable=self._controls_summary_var,
            justify="left",
            anchor="w",
            wraplength=500,
        )
        summary_label.pack(fill="x", pady=(12, 0))

        notice_label = self._ttkb.Label(
            root_frame,
            textvariable=self._controls_notice_var,
            justify="left",
            anchor="w",
            wraplength=500,
        )
        notice_label.pack(fill="x", pady=(8, 0))

        self._controls_content_frame = self._ttkb.Frame(root_frame)
        self._controls_content_frame.pack(
            fill="both", expand=True, pady=(12, 0)
        )

        button_row = self._ttkb.Frame(root_frame)
        button_row.pack(fill="x", pady=(16, 0))

        refresh_button = self._ttkb.Button(
            button_row,
            text="Refresh",
            command=self._refresh_cameras_action,
            bootstyle="secondary",
        )
        refresh_button.pack(side="left")

        open_button = self._ttkb.Button(
            button_row,
            text="Open",
            command=self.open_selected_camera,
            bootstyle="primary",
        )
        open_button.pack(side="left", padx=(12, 0))

        close_button = self._ttkb.Button(
            button_row,
            text="Hide",
            command=self._handle_controls_window_close,
            bootstyle="secondary",
        )
        close_button.pack(side="right")

        self._controls_window = controls_window
        self._sync_controls_summary()
        self._render_controls()

    def _controls_window_state(self) -> str:
        """Return whether the separate controls window is visible."""

        if self._controls_window is None:
            return "closed"
        if self._controls_window.state() == "withdrawn":
            return "closed"
        return "open"

    def _source_mode_label(self) -> str:
        """Return the current source-mode summary for the status bar."""

        width = getattr(self._backend, "preview_width", None)
        height = getattr(self._backend, "preview_height", None)
        if width is not None and height is not None:
            return f"{width}x{height}@30 preview"
        return "unavailable"

    def _sync_controls_summary(self) -> None:
        """Refresh the controls-window summary text."""

        self._controls_summary_var.set(self._build_controls_summary())

    def _clear_pending_control_apply(
        self, control_id: str | None = None
    ) -> None:
        """Cancel one or all queued numeric-control updates."""

        if control_id is None:
            control_ids = tuple(self._pending_control_apply_ids)
        else:
            control_ids = (control_id,)
        for queued_control_id in control_ids:
            after_id = self._pending_control_apply_ids.pop(
                queued_control_id,
                None,
            )
            if after_id is not None:
                self._window.after_cancel(after_id)

    def _schedule_numeric_control_apply(
        self,
        control_id: str,
        value: float,
    ) -> None:
        """Debounce numeric-control writes so slider motion stays smooth."""

        self._clear_pending_control_apply(control_id)
        after_id = self._window.after(
            self.control_apply_delay_ms,
            lambda cid=control_id, numeric_value=value: (
                self._execute_scheduled_numeric_apply(cid, numeric_value)
            ),
        )
        self._pending_control_apply_ids[control_id] = after_id

    def _execute_scheduled_numeric_apply(
        self,
        control_id: str,
        value: float,
    ) -> None:
        """Apply one queued numeric-control update."""

        self._pending_control_apply_ids.pop(control_id, None)
        self._apply_control_value(
            control_id,
            value,
            refresh_surface=False,
            status_notice=False,
        )

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

    def _handle_numeric_slider(
        self,
        control_id: str,
        raw_value: str,
    ) -> None:
        """Synchronize the numeric entry from the slider and queue apply."""

        control = self._controls_by_id.get(control_id)
        entry_var = self._numeric_entry_vars.get(control_id)
        if control is None or entry_var is None:
            return
        try:
            numeric_value = float(raw_value)
        except ValueError:
            return
        entry_var.set(
            format_numeric_control_value(
                numeric_value,
                control.step,
            )
        )
        self._schedule_numeric_control_apply(control_id, numeric_value)

    def _handle_numeric_entry_commit(self, control_id: str) -> None:
        """Commit one spinbox value or clear invalid text to blank."""

        control = self._controls_by_id.get(control_id)
        entry_var = self._numeric_entry_vars.get(control_id)
        scale_var = self._numeric_scale_vars.get(control_id)
        if (
            control is None
            or entry_var is None
            or scale_var is None
            or control.min_value is None
            or control.max_value is None
        ):
            return
        numeric_value = parse_numeric_control_text(
            entry_var.get(),
            minimum=control.min_value,
            maximum=control.max_value,
        )
        if numeric_value is None:
            entry_var.set("")
            self._set_controls_notice(
                f"{control.label} cleared an invalid value."
            )
            self._set_status(
                self._preview_state,
                notice=f"{control.label} cleared an invalid value.",
            )
            return
        scale_var.set(numeric_value)
        self._clear_pending_control_apply(control_id)
        self._apply_control_value(
            control_id,
            numeric_value,
            refresh_surface=False,
            status_notice=False,
        )

    def _handle_boolean_toggle(self, control_id: str) -> None:
        """Apply one boolean control from its checkbutton state."""

        variable = self._boolean_vars.get(control_id)
        if variable is None:
            return
        self._apply_control_value(
            control_id,
            bool(variable.get()),
            refresh_surface=True,
            status_notice=True,
        )

    def _handle_enum_selected(self, control_id: str) -> None:
        """Apply one enumerated control from the current combobox label."""

        variable = self._enum_vars.get(control_id)
        label_map = self._enum_label_maps.get(control_id)
        if variable is None or label_map is None:
            return
        label = variable.get()
        selected_value = label_map.get(label)
        if selected_value is None:
            return
        self._apply_control_value(
            control_id,
            selected_value,
            refresh_surface=True,
            status_notice=True,
        )

    def _render_control_details(
        self,
        parent,
        control: CameraControl,
    ) -> None:
        """Render optional helper text beneath one control row."""

        if not control.details:
            return
        details_label = self._ttkb.Label(
            parent,
            text=control.details,
            justify="left",
            wraplength=460,
        )
        details_label.pack(anchor="w", pady=(4, 0))

    def _render_numeric_control(self, parent, control: CameraControl) -> None:
        """Render one guvcview-style numeric control row."""

        import tkinter as tkinter_module

        if (
            control.min_value is None
            or control.max_value is None
            or control.value is None
        ):
            return
        frame = self._ttkb.Frame(parent, padding=(0, 4))
        frame.pack(fill="x", pady=(0, 8))

        label = self._ttkb.Label(frame, text=control.label)
        label.pack(anchor="w")

        widget_row = self._ttkb.Frame(frame)
        widget_row.pack(fill="x", pady=(4, 0))
        widget_row.grid_columnconfigure(0, weight=1)

        scale_var = tkinter_module.DoubleVar(value=float(control.value))
        entry_var = tkinter_module.StringVar(
            value=format_numeric_control_value(
                float(control.value),
                control.step,
            )
        )
        self._numeric_scale_vars[control.control_id] = scale_var
        self._numeric_entry_vars[control.control_id] = entry_var

        scale = self._ttkb.Scale(
            widget_row,
            from_=control.min_value,
            to=control.max_value,
            orient="horizontal",
            variable=scale_var,
            command=lambda raw_value, cid=control.control_id: (
                self._handle_numeric_slider(cid, raw_value)
            ),
        )
        scale.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        if control.read_only or not control.enabled:
            scale.configure(state="disabled")

        spinbox = self._ttkb.Spinbox(
            widget_row,
            from_=control.min_value,
            to=control.max_value,
            increment=control.step or 1.0,
            textvariable=entry_var,
            width=10,
            command=lambda cid=control.control_id: (
                self._handle_numeric_entry_commit(cid)
            ),
        )
        spinbox.grid(row=0, column=1, sticky="e")
        spinbox.bind(
            "<Return>",
            lambda _event, cid=control.control_id: (
                self._handle_numeric_entry_commit(cid)
            ),
        )
        spinbox.bind(
            "<FocusOut>",
            lambda _event, cid=control.control_id: (
                self._handle_numeric_entry_commit(cid)
            ),
        )
        if control.read_only or not control.enabled:
            spinbox.configure(state="disabled")

        labels_row = self._ttkb.Frame(frame)
        labels_row.pack(fill="x")
        labels_row.grid_columnconfigure(0, weight=1)
        labels_row.grid_columnconfigure(1, weight=1)
        labels_row.grid_columnconfigure(2, weight=1)

        midpoint = (control.min_value + control.max_value) / 2
        for column, value in enumerate(
            (
                control.min_value,
                midpoint,
                control.max_value,
            )
        ):
            value_text = format_numeric_control_value(value, control.step)
            if control.unit:
                value_text = f"{value_text} {control.unit}"
            anchor = "w" if column == 0 else "center"
            if column == 2:
                anchor = "e"
            label = self._ttkb.Label(
                labels_row, text=value_text, anchor=anchor
            )
            label.grid(row=0, column=column, sticky="ew")

        self._render_control_details(frame, control)

    def _render_boolean_control(self, parent, control: CameraControl) -> None:
        """Render one boolean control row."""

        import tkinter as tkinter_module

        frame = self._ttkb.Frame(parent, padding=(0, 4))
        frame.pack(fill="x", pady=(0, 8))

        variable = tkinter_module.BooleanVar(value=bool(control.value))
        self._boolean_vars[control.control_id] = variable

        checkbutton = self._ttkb.Checkbutton(
            frame,
            text=control.label,
            variable=variable,
            command=lambda cid=control.control_id: (
                self._handle_boolean_toggle(cid)
            ),
        )
        checkbutton.pack(anchor="w")
        if control.read_only or not control.enabled:
            checkbutton.configure(state="disabled")

        self._render_control_details(frame, control)

    def _render_enum_control(self, parent, control: CameraControl) -> None:
        """Render one enumerated control row."""

        import tkinter as tkinter_module

        frame = self._ttkb.Frame(parent, padding=(0, 4))
        frame.pack(fill="x", pady=(0, 8))

        label = self._ttkb.Label(frame, text=control.label)
        label.pack(anchor="w")

        label_map = {choice.label: choice.value for choice in control.choices}
        value_map = {choice.value: choice.label for choice in control.choices}
        variable = tkinter_module.StringVar(
            value=value_map.get(str(control.value), "")
        )
        self._enum_vars[control.control_id] = variable
        self._enum_label_maps[control.control_id] = label_map

        combo = self._ttkb.Combobox(
            frame,
            state="readonly",
            textvariable=variable,
            values=tuple(label_map),
        )
        combo.pack(fill="x", pady=(4, 0))
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event, cid=control.control_id: (
                self._handle_enum_selected(cid)
            ),
        )
        if control.read_only or not control.enabled:
            combo.configure(state="disabled")

        self._render_control_details(frame, control)

    def _render_read_only_control(
        self, parent, control: CameraControl
    ) -> None:
        """Render one read-only control row."""

        frame = self._ttkb.Frame(parent, padding=(0, 4))
        frame.pack(fill="x", pady=(0, 8))

        label = self._ttkb.Label(frame, text=f"{control.label}:")
        label.pack(anchor="w")

        value_label = self._ttkb.Label(
            frame,
            text=str(control.value),
            justify="left",
            wraplength=460,
        )
        value_label.pack(anchor="w", pady=(2, 0))

        self._render_control_details(frame, control)

    def _render_action_control(self, parent, control: CameraControl) -> None:
        """Render one action control row."""

        frame = self._ttkb.Frame(parent, padding=(0, 4))
        frame.pack(fill="x", pady=(0, 8))

        button = self._ttkb.Button(
            frame,
            text=control.action_label or control.label,
            command=lambda cid=control.control_id: (
                self._trigger_control_action(cid)
            ),
            bootstyle="secondary",
        )
        button.pack(anchor="w")
        if control.read_only or not control.enabled:
            button.configure(state="disabled")

        details_text = control.details or control.label
        details_label = self._ttkb.Label(
            frame,
            text=details_text,
            justify="left",
            wraplength=460,
        )
        details_label.pack(anchor="w", pady=(4, 0))

    def _render_control_section(
        self,
        parent,
        *,
        heading: str,
        controls: tuple[CameraControl, ...],
    ) -> None:
        """Render one grouped control section inside the controls window."""

        if not controls:
            return
        section = self._ttkb.Labelframe(parent, text=heading, padding=12)
        section.pack(fill="x", pady=(0, 12))
        for control in controls:
            if control.kind == "numeric":
                self._render_numeric_control(section, control)
            elif control.kind == "boolean":
                self._render_boolean_control(section, control)
            elif control.kind == "enum":
                self._render_enum_control(section, control)
            elif control.kind == "read_only":
                self._render_read_only_control(section, control)
            elif control.kind == "action":
                self._render_action_control(section, control)

    def _render_controls(self) -> None:
        """Render the current control surface into the separate window."""

        if self._controls_content_frame is None:
            return
        for child in self._controls_content_frame.winfo_children():
            child.destroy()
        self._numeric_scale_vars.clear()
        self._numeric_entry_vars.clear()
        self._boolean_vars.clear()
        self._enum_vars.clear()
        self._enum_label_maps.clear()

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
            empty_label = self._ttkb.Label(
                self._controls_content_frame,
                text=(
                    "No camera controls are currently available for the "
                    "selected camera/backend."
                ),
                justify="left",
                wraplength=500,
            )
            empty_label.pack(anchor="w")
            return

        self._render_control_section(
            self._controls_content_frame,
            heading="Numeric Controls",
            controls=tuple(controls_by_kind["numeric"]),
        )
        self._render_control_section(
            self._controls_content_frame,
            heading="Toggle Controls",
            controls=tuple(controls_by_kind["boolean"]),
        )
        self._render_control_section(
            self._controls_content_frame,
            heading="Enumerated Controls",
            controls=tuple(controls_by_kind["enum"]),
        )
        self._render_control_section(
            self._controls_content_frame,
            heading="Read-Only Details",
            controls=tuple(controls_by_kind["read_only"]),
        )
        self._render_control_section(
            self._controls_content_frame,
            heading="Actions",
            controls=tuple(controls_by_kind["action"]),
        )

    def _toggle_controls_window(self) -> None:
        """Open or close the separate controls window."""

        self._ensure_controls_window()
        assert self._controls_window is not None
        if self._controls_window_state() == "open":
            self._handle_controls_window_close()
            return
        self._controls_window.deiconify()
        self._controls_window.lift()
        self._refresh_control_surface(notice="Controls window open.")
        self._set_status(self._preview_state, notice="Controls window open.")

    def _handle_controls_window_close(self) -> None:
        """Hide the separate controls window without closing the app."""

        if self._controls_window is None:
            return
        self._controls_window.withdraw()
        self._set_status(self._preview_state, notice="Controls window closed.")

    def _refresh_cameras_action(self) -> None:
        """Refresh cameras from toolbar and menu actions."""

        self.refresh_cameras(auto_open=True)

    def _close_camera_action(self) -> None:
        """Close the active camera session from the shell."""

        self.close_session()
        self._set_preview_message("Camera session closed.")
        self._refresh_control_surface(notice="Camera session closed.")
        self._set_status("idle", notice="Camera session closed.")

    def _capture_still_action(self) -> None:
        """Announce the staged still-capture placeholder."""

        self._set_status(
            self._preview_state,
            notice="Still capture lands in Item 6.",
        )

    def _toggle_recording_action(self) -> None:
        """Announce the staged recording placeholder."""

        self._set_status(
            self._preview_state,
            notice="Recording lands in Item 6.",
        )

    def _toggle_fullscreen(self) -> None:
        """Toggle the main window between windowed and fullscreen states."""

        self._is_fullscreen = not self._is_fullscreen
        self._window.attributes("-fullscreen", self._is_fullscreen)
        mode = "Fullscreen" if self._is_fullscreen else "Windowed"
        self._set_status(
            self._preview_state,
            notice=f"{mode} view active.",
        )

    def _open_preferences(self) -> None:
        """Announce the staged preferences placeholder."""

        self._set_status(
            self._preview_state,
            notice="Preferences and shortcuts land in Item 7.",
        )

    def _open_diagnostics(self) -> None:
        """Announce the staged diagnostics placeholder."""

        self._set_status(
            self._preview_state,
            notice="Diagnostics surface lands in Item 8.",
        )

    def _show_about(self) -> None:
        """Show an about summary through the status surface."""

        self._set_status(
            self._preview_state,
            notice=(
                f"{APP_NAME} uses {GUI_BASELINE} with "
                f"{self._backend.backend_name} preview."
            ),
        )

    def _set_status(
        self, preview_state: str, *, notice: str | None = None
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
            framing_mode=self._framing_mode,
            controls_window_state=self._controls_window_state(),
            recording_state=self._recording_state,
            notice=self._status_notice,
        )
        self._status_var.set(
            self._spec.status_template.format(
                backend=status.backend_name,
                camera=status.camera_name,
                source=status.source_mode,
                framing=status.framing_mode,
                controls=status.controls_window_state,
                recording=status.recording_state,
                notice=status.notice,
            )
        )
        self._sync_controls_summary()

    def _set_preview_message(self, message: str) -> None:
        """Show preview status text and clear any stale frame image."""

        self._preview_image = None
        self._preview_label.configure(
            image="",
            text=message,
            compound="center",
        )
        self._sync_controls_summary()

    def _selected_camera_name(self) -> str:
        """Return the current camera label for the status bar."""

        descriptor = self._selected_descriptor()
        if descriptor is None:
            return "none"
        return descriptor.display_name

    def refresh_cameras(self, *, auto_open: bool) -> None:
        """Refresh the discovered camera list and optionally open one."""

        self.close_session()
        self._cameras = self._backend.discover_cameras()
        names = [descriptor.display_name for descriptor in self._cameras]
        self._camera_combo["values"] = names
        if not names:
            self._selected_camera_index = None
            self._camera_var.set("")
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
        self._selected_camera_index = 0
        self._camera_var.set(names[0])
        self._set_preview_message("Opening camera...")
        self._refresh_control_surface(notice="Camera list refreshed.")
        self._set_status("camera ready", notice="Camera list refreshed.")
        if auto_open:
            self.open_selected_camera()

    def _on_camera_selected(self, _event=None) -> None:
        """Handle a camera selection change from the combobox."""

        selected_name = self._camera_var.get()
        for index, descriptor in enumerate(self._cameras):
            if descriptor.display_name == selected_name:
                self._selected_camera_index = index
                break
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

    def _tick_preview(self) -> None:
        """Poll the newest frame and refresh the preview without lagging."""

        if self._closed:
            return
        if self._session is not None:
            failure_reason = self._session.failure_reason
            if failure_reason:
                self._set_preview_message(failure_reason)
                self._set_status(
                    "preview failed",
                    notice="Preview failed; see on-screen error.",
                )
                self._window.after(
                    self.refresh_interval_ms, self._tick_preview
                )
                return
            frame = self._session.get_latest_frame()
            if (
                frame is not None
                and frame.frame_number != self._last_frame_number
            ):
                from PIL import ImageTk

                self._last_frame_number = frame.frame_number
                image = Image.frombytes(
                    "RGB",
                    (frame.width, frame.height),
                    frame.rgb_bytes,
                )
                image.thumbnail((960, 640))
                photo = ImageTk.PhotoImage(image=image)
                self._preview_image = photo
                self._preview_label.configure(
                    image=photo,
                    text="",
                    compound="center",
                )
                self._set_status("live", notice="Live preview active.")
        self._window.after(self.refresh_interval_ms, self._tick_preview)

    def close_session(self) -> None:
        """Close the current camera session if one is active."""

        self._clear_pending_control_apply()
        if self._session is None:
            return
        self._session.close()
        self._session = None
        self._last_frame_number = -1
        self._sync_controls_summary()

    def _handle_close(self) -> None:
        """Shut down preview resources before closing the window."""

        self._closed = True
        self._clear_pending_control_apply()
        self.close_session()
        if self._controls_window is not None:
            self._controls_window.destroy()
        self._window.destroy()

    def run(self) -> int:
        """Start the Tk main loop for the preview application."""

        self._window.mainloop()
        return 0


def launch_main_window() -> int:
    """Launch the Stage 4 controls-aware workspace."""

    try:
        import ttkbootstrap as ttkb
    except ModuleNotFoundError as exc:
        raise MissingGuiDependencyError(
            "Install the package runtime dependencies before launching the "
            "GUI shell."
        ) from exc

    application = PreviewApplication(ttkb)
    return application.run()
