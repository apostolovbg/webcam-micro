"""GUI shell assembly for the Stage 1 prototype foundation."""

from __future__ import annotations

from dataclasses import dataclass

from webcam_micro import APP_NAME, GUI_BASELINE, SHELL_TITLE
from webcam_micro.camera import build_backend_plan


class MissingGuiDependencyError(RuntimeError):
    """Raised when the GUI dependency set is not installed."""


@dataclass(frozen=True)
class ShellSpec:
    """Describe the headless-friendly shape of the first GUI shell."""

    title: str
    theme_name: str
    hero_title: str
    hero_body: tuple[str, ...]


def build_shell_spec() -> ShellSpec:
    """Return the Stage 1 GUI-shell description."""

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
    )


def launch_main_window() -> int:
    """Launch the minimal Stage 1 GUI shell."""

    try:
        import ttkbootstrap as ttkb
    except ModuleNotFoundError as exc:
        raise MissingGuiDependencyError(
            "Install the package runtime dependencies before launching the "
            "GUI shell."
        ) from exc

    spec = build_shell_spec()
    window = ttkb.Window(themename=spec.theme_name)
    window.title(spec.title)
    window.geometry("960x640")
    window.minsize(720, 480)

    root_frame = ttkb.Frame(window, padding=24)
    root_frame.pack(fill="both", expand=True)

    hero_frame = ttkb.Labelframe(root_frame, text="Stage 1 foundation")
    hero_frame.pack(fill="both", expand=True)

    title_label = ttkb.Label(
        hero_frame,
        text=spec.hero_title,
        font=("TkDefaultFont", 18, "bold"),
    )
    title_label.pack(anchor="w", padx=16, pady=(16, 8))

    for line in spec.hero_body:
        body_label = ttkb.Label(hero_frame, text=line, wraplength=760)
        body_label.pack(anchor="w", padx=16, pady=4)

    window.mainloop()
    return 0
