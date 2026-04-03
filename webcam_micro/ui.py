"""GUI shell assembly for the Stage 2 preview baseline."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from webcam_micro import APP_NAME, GUI_BASELINE, SHELL_TITLE
from webcam_micro.camera import (
    CameraDescriptor,
    FfmpegCameraBackend,
    MissingCameraDependencyError,
    NullCameraBackend,
    build_backend_plan,
)


class MissingGuiDependencyError(RuntimeError):
    """Raised when the GUI dependency set is not installed."""


@dataclass(frozen=True)
class ShellSpec:
    """Describe the working shape of the Stage 2 preview shell."""

    title: str
    theme_name: str
    hero_title: str
    hero_body: tuple[str, ...]
    status_template: str


def build_shell_spec() -> ShellSpec:
    """Return the Stage 2 preview-shell description."""

    backend_plan = build_backend_plan()
    return ShellSpec(
        title=SHELL_TITLE,
        theme_name="litera",
        hero_title=APP_NAME,
        hero_body=(
            "Preview-first microscope camera prototype shell.",
            f"GUI baseline: {GUI_BASELINE}",
            "Backend baseline: " f"{backend_plan.first_device_backend_target}",
        ),
        status_template=(
            "Backend: {backend} | Camera: {camera} | Preview: {preview}"
        ),
    )


@dataclass(frozen=True)
class RuntimeStatus:
    """Describe the visible runtime status shown in the main shell."""

    backend_name: str
    camera_name: str
    preview_state: str


def build_runtime_status(
    backend_name: str,
    camera_name: str,
    preview_state: str,
) -> RuntimeStatus:
    """Return one visible runtime-status snapshot for the status bar."""

    return RuntimeStatus(
        backend_name=backend_name,
        camera_name=camera_name,
        preview_state=preview_state,
    )


class PreviewApplication:
    """Manage camera discovery, sessions, and preview updates for Tk."""

    refresh_interval_ms = 15

    def __init__(self, ttkb_module) -> None:
        """Build the Stage 2 preview shell and initialize runtime state."""

        self._ttkb = ttkb_module
        self._window = ttkb_module.Window(
            themename=build_shell_spec().theme_name
        )
        self._window.title(build_shell_spec().title)
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

        self._camera_var = ttkb_module.StringVar(value="")
        self._status_var = ttkb_module.StringVar(value="")

        self._build_layout()
        self.refresh_cameras(auto_open=True)
        self._window.after(self.refresh_interval_ms, self._tick_preview)

    def _build_backend(self):
        """Return the active preview backend or a null fallback."""

        try:
            return FfmpegCameraBackend()
        except MissingCameraDependencyError:
            return NullCameraBackend()

    def _build_layout(self) -> None:
        """Build the preview-first Stage 2 shell."""

        spec = build_shell_spec()
        root_frame = self._ttkb.Frame(self._window, padding=16)
        root_frame.pack(fill="both", expand=True)

        top_frame = self._ttkb.Frame(root_frame)
        top_frame.pack(fill="x", pady=(0, 12))

        title_label = self._ttkb.Label(
            top_frame,
            text=spec.hero_title,
            font=("TkDefaultFont", 20, "bold"),
        )
        title_label.pack(side="left")

        backend_label = self._ttkb.Label(
            top_frame,
            text=f"Backend: {self._backend.backend_name}",
        )
        backend_label.pack(side="right")

        controls_frame = self._ttkb.Frame(root_frame)
        controls_frame.pack(fill="x", pady=(0, 12))

        self._camera_combo = self._ttkb.Combobox(
            controls_frame,
            textvariable=self._camera_var,
            state="readonly",
            width=36,
        )
        self._camera_combo.pack(side="left", fill="x", expand=True)
        self._camera_combo.bind(
            "<<ComboboxSelected>>",
            self._on_camera_selected,
        )

        refresh_button = self._ttkb.Button(
            controls_frame,
            text="Refresh Cameras",
            command=lambda: self.refresh_cameras(auto_open=True),
            bootstyle="secondary",
        )
        refresh_button.pack(side="left", padx=(12, 0))

        open_button = self._ttkb.Button(
            controls_frame,
            text="Open Camera",
            command=self.open_selected_camera,
            bootstyle="primary",
        )
        open_button.pack(side="left", padx=(12, 0))

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

        for line in spec.hero_body:
            body_label = self._ttkb.Label(root_frame, text=line)
            body_label.pack(anchor="w")

        status_bar = self._ttkb.Label(
            self._window,
            textvariable=self._status_var,
            anchor="w",
            padding=(12, 6),
        )
        status_bar.pack(fill="x", side="bottom")
        self._set_status("idle")

    def _set_status(self, preview_state: str) -> None:
        """Render the current backend, camera, and preview state."""

        spec = build_shell_spec()
        status = build_runtime_status(
            backend_name=self._backend.backend_name,
            camera_name=self._selected_camera_name(),
            preview_state=preview_state,
        )
        self._status_var.set(
            spec.status_template.format(
                backend=status.backend_name,
                camera=status.camera_name,
                preview=status.preview_state,
            )
        )

    def _set_preview_message(self, message: str) -> None:
        """Show preview status text and clear any stale frame image."""

        self._preview_image = None
        self._preview_label.configure(
            image="",
            text=message,
            compound="center",
        )

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
            self._set_status("no devices")
            return
        self._selected_camera_index = 0
        self._camera_var.set(names[0])
        self._set_preview_message("Opening camera...")
        self._set_status("camera ready")
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
            self._set_status("no selection")
            return
        descriptor = self._cameras[self._selected_camera_index]
        self.close_session()
        try:
            self._session = self._backend.open_session(descriptor)
        except RuntimeError as exc:
            self._set_preview_message(str(exc))
            self._set_status("open failed")
            return
        self._set_preview_message("Waiting for live preview frames...")
        self._set_status("opening")

    def _tick_preview(self) -> None:
        """Poll the newest frame and refresh the preview without lagging."""

        if self._closed:
            return
        if self._session is not None:
            failure_reason = self._session.failure_reason
            if failure_reason:
                self._set_preview_message(failure_reason)
                self._set_status("preview failed")
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
                self._set_status("live")
        self._window.after(self.refresh_interval_ms, self._tick_preview)

    def close_session(self) -> None:
        """Close the current camera session if one is active."""

        if self._session is None:
            return
        self._session.close()
        self._session = None
        self._last_frame_number = -1

    def _handle_close(self) -> None:
        """Shut down preview resources before closing the window."""

        self._closed = True
        self.close_session()
        self._window.destroy()

    def run(self) -> int:
        """Start the Tk main loop for the preview application."""

        self._window.mainloop()
        return 0


def launch_main_window() -> int:
    """Launch the Stage 2 preview shell."""

    try:
        import ttkbootstrap as ttkb
    except ModuleNotFoundError as exc:
        raise MissingGuiDependencyError(
            "Install the package runtime dependencies before launching the "
            "GUI shell."
        ) from exc

    application = PreviewApplication(ttkb)
    return application.run()
