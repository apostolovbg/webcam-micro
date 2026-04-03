"""GUI shell assembly for the Stage 3 preview-first workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image

from webcam_micro import APP_NAME, GUI_BASELINE, SHELL_TITLE
from webcam_micro.camera import (
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
    """Describe the working shape of the Stage 3 main window."""

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
    """Return the Stage 3 preview-first shell description."""

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


class PreviewApplication:
    """Manage camera discovery, sessions, and preview updates for Tk."""

    refresh_interval_ms = 15

    def __init__(self, ttkb_module) -> None:
        """Build the Stage 3 shell and initialize runtime state."""

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
        self._preview_image = None
        self._last_frame_number = -1
        self._closed = False
        self._is_fullscreen = False
        self._controls_window: tkinter_module.Toplevel | None = None
        self._controls_summary_var = ttkb_module.StringVar(value="")
        self._preview_state = "idle"
        self._framing_mode = "fit"
        self._recording_state = "not ready"
        self._status_notice = "Workspace ready."

        self._camera_var = ttkb_module.StringVar(value="")
        self._status_var = ttkb_module.StringVar(value="")

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
        """Build the preview-first Stage 3 shell."""

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

    def _build_controls_summary(self) -> str:
        """Return the visible summary shown in the controls window."""

        lines = [
            f"Backend: {self._backend.backend_name}",
            f"Camera: {self._selected_camera_name()}",
            f"Preview: {self._preview_state}",
            f"Source mode: {self._source_mode_label()}",
            f"Framing mode: {self._framing_mode}",
            "",
            "Camera controls land in Item 4. This separate window already",
            "protects preview space while keeping session state visible.",
        ]
        return "\n".join(lines)

    def _ensure_controls_window(self) -> None:
        """Create the separate controls window when first requested."""

        import tkinter as tkinter_module

        if self._controls_window is not None:
            return
        controls_window = tkinter_module.Toplevel(self._window)
        controls_window.title(self._spec.controls_window_title)
        controls_window.geometry("420x260")
        controls_window.minsize(320, 220)
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
            wraplength=360,
        )
        summary_label.pack(fill="x", pady=(12, 0))

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

    def _toggle_controls_window(self) -> None:
        """Open or close the separate controls window."""

        self._ensure_controls_window()
        assert self._controls_window is not None
        if self._controls_window_state() == "open":
            self._handle_controls_window_close()
            return
        self._controls_window.deiconify()
        self._controls_window.lift()
        self._sync_controls_summary()
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

        if self._selected_camera_index is None:
            return "none"
        if 0 <= self._selected_camera_index < len(self._cameras):
            return self._cameras[self._selected_camera_index].display_name
        return "none"

    def refresh_cameras(self, *, auto_open: bool) -> None:
        """Refresh the discovered camera list and optionally open one."""

        self.close_session()
        self._cameras = self._backend.discover_cameras()
        names = [descriptor.display_name for descriptor in self._cameras]
        self._camera_combo["values"] = names
        if not names:
            self._selected_camera_index = None
            self._camera_var.set("")
            if self._backend.backend_name == "null":
                self._set_preview_message(
                    "Camera runtime backend is unavailable.\n"
                    "Install package runtime dependencies and relaunch."
                )
            else:
                self._set_preview_message(
                    "No cameras detected.\nConnect a camera and refresh."
                )
            self._set_status(
                "no devices", notice="No camera devices detected."
            )
            return
        self._selected_camera_index = 0
        self._camera_var.set(names[0])
        self._set_preview_message("Opening camera...")
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

        if self._selected_camera_index is None:
            self._set_preview_message("No camera selected.")
            self._set_status("no selection", notice="Choose a camera first.")
            return
        descriptor = self._cameras[self._selected_camera_index]
        self.close_session()
        try:
            self._session = self._backend.open_session(descriptor)
        except RuntimeError as exc:
            self._set_preview_message(str(exc))
            self._set_status("open failed", notice="Camera open failed.")
            return
        self._set_preview_message("Waiting for live preview frames...")
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

        if self._session is None:
            return
        self._session.close()
        self._session = None
        self._last_frame_number = -1
        self._sync_controls_summary()

    def _handle_close(self) -> None:
        """Shut down preview resources before closing the window."""

        self._closed = True
        self.close_session()
        if self._controls_window is not None:
            self._controls_window.destroy()
        self._window.destroy()

    def run(self) -> int:
        """Start the Tk main loop for the preview application."""

        self._window.mainloop()
        return 0


def launch_main_window() -> int:
    """Launch the Stage 3 preview-first workspace."""

    try:
        import ttkbootstrap as ttkb
    except ModuleNotFoundError as exc:
        raise MissingGuiDependencyError(
            "Install the package runtime dependencies before launching the "
            "GUI shell."
        ) from exc

    application = PreviewApplication(ttkb)
    return application.run()
