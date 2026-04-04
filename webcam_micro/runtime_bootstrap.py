"""Bootstrap a stable per-user Python runtime before the app launches."""

from __future__ import annotations

import os
import plistlib
import site
import sys
import sysconfig
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from webcam_micro import APP_NAME, PACKAGE_NAME

CAMERA_USAGE_DESCRIPTION = (
    "webcam-micro needs camera access to open the microscope preview."
)


@dataclass(frozen=True)
class RuntimeBootstrapPlan:
    """Describe the runtime interpreter and import bridge in use."""

    runtime_root: Path
    runtime_python: Path
    runtime_site_packages: Path
    import_roots: tuple[Path, ...]
    needs_runtime_creation: bool
    needs_relaunch: bool
    macos_info_plist: Path | None


def build_runtime_bootstrap_plan() -> RuntimeBootstrapPlan:
    """Return the current bootstrap plan without changing the filesystem."""

    runtime_root = _runtime_root()
    runtime_python = _runtime_python_path(runtime_root)
    runtime_site_packages = _runtime_site_packages_path(runtime_root)
    import_roots = _bridge_import_roots(runtime_root)
    current_python = Path(sys.executable).resolve()
    target_python = runtime_python.resolve(strict=False)
    return RuntimeBootstrapPlan(
        runtime_root=runtime_root,
        runtime_python=runtime_python,
        runtime_site_packages=runtime_site_packages,
        import_roots=import_roots,
        needs_runtime_creation=not runtime_python.exists(),
        needs_relaunch=current_python != target_python,
        macos_info_plist=_macos_info_plist(),
    )


def bootstrap_runtime(argv: Sequence[str] | None = None) -> None:
    """Create or reuse the private runtime interpreter and relaunch into it."""

    argv_list = list(sys.argv[1:] if argv is None else argv)
    plan = build_runtime_bootstrap_plan()
    if plan.needs_runtime_creation:
        _create_runtime_environment(plan.runtime_root)
    if plan.needs_relaunch:
        _write_import_bridge(plan.runtime_site_packages, plan.import_roots)
    if plan.macos_info_plist is not None:
        _ensure_camera_usage_description(plan.macos_info_plist)
    if plan.needs_relaunch:
        _exec_runtime_python(plan.runtime_python, argv_list)


def _create_runtime_environment(runtime_root: Path) -> None:
    """Materialize a private venv at the stable per-user runtime root."""

    runtime_root.mkdir(parents=True, exist_ok=True)
    builder = venv.EnvBuilder(with_pip=True, symlinks=False)
    builder.create(runtime_root)


def _exec_runtime_python(runtime_python: Path, argv: Sequence[str]) -> None:
    """Re-exec the launcher through the private runtime interpreter."""

    os.execv(
        str(runtime_python),
        [str(runtime_python), "-m", PACKAGE_NAME, *argv],
    )


def _runtime_root() -> Path:
    """Return the stable per-user directory for the private runtime."""

    if sys.platform == "darwin":
        base_root = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_root = Path(local_app_data)
        else:
            base_root = Path.home() / "AppData" / "Local"
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base_root = Path(xdg_data_home)
        else:
            base_root = Path.home() / ".local" / "share"
    return base_root / APP_NAME / "python-runtime"


def _runtime_python_path(runtime_root: Path) -> Path:
    """Return the runtime interpreter path for the current platform."""

    if sys.platform == "win32":
        return runtime_root / "Scripts" / "python.exe"
    return runtime_root / "bin" / "python"


def _runtime_site_packages_path(runtime_root: Path) -> Path:
    """Return the runtime site-packages directory for the venv root."""

    purelib = sysconfig.get_path(
        "purelib",
        vars={
            "base": str(runtime_root),
            "platbase": str(runtime_root),
        },
    )
    if purelib is None:
        raise RuntimeError("Unable to resolve the runtime site-packages path.")
    return Path(purelib)


def _bridge_import_roots(runtime_root: Path) -> tuple[Path, ...]:
    """Return import roots to mirror into the private runtime."""

    candidates: list[Path] = [Path(__file__).resolve().parents[1]]
    for site_root in _site_paths():
        candidates.append(site_root)

    roots: list[Path] = []
    for candidate in candidates:
        if not candidate.is_absolute():
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not resolved.exists():
            continue
        if resolved == runtime_root or runtime_root in resolved.parents:
            continue
        if resolved not in roots:
            roots.append(resolved)
    return tuple(roots)


def _site_paths() -> tuple[Path, ...]:
    """Return the current interpreter's site-package roots."""

    paths: list[Path] = []
    try:
        paths.extend(Path(path) for path in site.getsitepackages())
    except AttributeError:
        pass
    user_site = site.getusersitepackages()
    if isinstance(user_site, str):
        paths.append(Path(user_site))
    elif isinstance(user_site, (list, tuple)):
        paths.extend(Path(path) for path in user_site)
    return tuple(path for path in paths if path)


def _write_import_bridge(
    runtime_site_packages: Path,
    import_roots: Sequence[Path],
) -> None:
    """Write the runtime .pth bridge that keeps imports working."""

    runtime_site_packages.mkdir(parents=True, exist_ok=True)
    bridge_file = runtime_site_packages / "webcam_micro_runtime.pth"
    bridge_lines = [str(path) for path in import_roots]
    bridge_text = "\n".join(bridge_lines) + "\n"
    if bridge_file.exists():
        current_text = bridge_file.read_text(encoding="utf-8")
        if current_text == bridge_text:
            return
    bridge_file.write_text(bridge_text, encoding="utf-8")


def _macos_info_plist() -> Path | None:
    """Return the active Python framework Info.plist when available."""

    if sys.platform != "darwin":
        return None
    info_plist = Path(sys.base_prefix) / "Resources" / "Info.plist"
    if info_plist.exists():
        return info_plist
    return None


def _ensure_camera_usage_description(info_plist: Path) -> None:
    """Add the camera usage description to the active Python framework."""

    with info_plist.open("rb") as handle:
        payload = plistlib.load(handle)
    if not isinstance(payload, dict):
        payload = {}
    if payload.get("NSCameraUsageDescription") == CAMERA_USAGE_DESCRIPTION:
        return
    payload["NSCameraUsageDescription"] = CAMERA_USAGE_DESCRIPTION
    with info_plist.open("wb") as handle:
        plistlib.dump(
            payload,
            handle,
            fmt=plistlib.FMT_XML,
            sort_keys=True,
        )
