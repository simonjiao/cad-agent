"""Windows-only stdio launcher for U-C4N AutoCAD MCP Pro 1.8.0.

All output before MCP startup must go to stderr, never stdout.
"""
from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path
import sys

EXPECTED_DIST_VERSION = "1.8.0"
PROGID = "AutoCAD.Application.23.0"  # AutoCAD 2019, per Autodesk
MODE_CHOICES = {"readonly", "sandbox"}


def read_mode(root: Path) -> str:
    mode_file = root / "mode.txt"
    try:
        mode = mode_file.read_text(encoding="utf-8-sig").strip().lower()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing {mode_file}; run Windows installer first") from exc
    if mode not in MODE_CHOICES:
        raise RuntimeError(f"Invalid {mode_file}: use readonly or sandbox, got {mode!r}")
    return mode


def make_server_env(root: Path, mode: str) -> dict[str, str]:
    """Return explicit server settings; no inherited overrides of security controls."""
    if mode not in MODE_CHOICES:
        raise ValueError("mode must be readonly or sandbox")
    work = root / "work"
    if not work.is_dir():
        raise RuntimeError(f"Missing work directory: {work}")
    return {
        "AUTOCAD_MCP_BACKEND": "com",     # no silent fallback to DXF
        "CAD_PROGID": PROGID,
        "CAD_LAUNCH": "never",           # attach only, never start CAD
        "ALLOWED_PATHS": str(work.resolve()),
        "DISCOVERY_MODE": "search",      # small tool list, tools searchable
        "TOOL_PROFILE": "full",
        "TOOL_PACKS": "core",
        "ENABLE_3D": "false",
        "READ_ONLY": "true" if mode == "readonly" else "false",
        "MAX_TOOL_COST": "read" if mode == "readonly" else "mutate",
        # Do not let raw AutoCAD commands / LISP bypass typed tools
        "TOOL_DENYLIST": (
            "system_run_command,system_run_lisp,"
            "drawing_open,drawing_new,drawing_close,"
            "document_activate,document_close,system_launch"
        ),
        "DANGEROUS_COMMANDS_ENABLED": "false",
        "LISP_POLICY": "read",
        "LOG_LEVEL": "WARNING",
        "PYTHONIOENCODING": "utf-8",
    }


def require_live_autocad(root: Path, mode: str) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        try:
            app = win32com.client.GetActiveObject(PROGID)
            version = str(app.Version)
        except Exception as exc:
            raise RuntimeError(
                "Cannot attach to RUNNING AutoCAD 2019 via " + PROGID
                + "; launch the full AutoCAD 2019 desktop first."
            ) from exc
        if not version.startswith("23.0"):
            raise RuntimeError(f"Wrong AutoCAD version: {version!r}; expected 23.0*")
        if mode == "sandbox":
            # Startup-only guard. Keep the test DWG active throughout the agent session.
            expected = root / "work" / "ai_demo_working.dwg"
            if not expected.is_file():
                raise RuntimeError(f"Sandbox drawing does not exist: {expected}; run create_demo.py")
            try:
                active = Path(str(app.ActiveDocument.FullName)).resolve()
            except Exception as exc:
                raise RuntimeError("Cannot read active AutoCAD document path") from exc
            if os.path.normcase(str(active)) != os.path.normcase(str(expected.resolve())):
                raise RuntimeError(
                    "Refusing writable MCP: active drawing is not the test copy. "
                    f"Active={active}; required={expected}"
                )
    finally:
        pythoncom.CoUninitialize()


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("Run this bridge using Windows Python.exe, not WSL Linux Python")
    root = Path(__file__).resolve().parent.parent
    mode = read_mode(root)
    for key, value in make_server_env(root, mode).items():
        os.environ[key] = value
    version = importlib.metadata.version("autocad-mcp-pro")
    if version != EXPECTED_DIST_VERSION:
        raise RuntimeError(
            f"Installed autocad-mcp-pro is {version}, expected {EXPECTED_DIST_VERSION}; "
            "run windows\\install.ps1"
        )
    require_live_autocad(root, mode)
    # U-C4N PyPI entry point is server:main (confirmed in v1.8.0 pyproject.toml).
    from server import main as server_main

    server_main()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[cad2019 bridge] {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
