"""Small Windows/pywin32 helpers; this file is not part of MCP protocol."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

PROGID = "AutoCAD.Application.23.0"
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
BASELINE = WORK / "ai_demo_baseline.dwg"
WORKING = WORK / "ai_demo_working.dwg"
BASELINE_HASH = WORK / "ai_demo_baseline.sha256"


def attach():
    if sys.platform != "win32":
        raise RuntimeError("This script requires native Windows Python + AutoCAD 2019")
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        app = win32com.client.GetActiveObject(PROGID)
    except Exception as exc:
        pythoncom.CoUninitialize()
        raise RuntimeError(
            "AutoCAD 2019 COM is not accessible. Launch AutoCAD 2019 full edition, "
            "open a DWG, then retry. Use the same Windows account and integrity level."
        ) from exc
    version = str(app.Version)
    if not version.startswith("23.0"):
        pythoncom.CoUninitialize()
        raise RuntimeError(f"Found AutoCAD {version!r}; expected 23.0* (2019)")
    return pythoncom, app, version


def release(pythoncom):
    pythoncom.CoUninitialize()


def point(x, y, z=0.0):
    import pythoncom
    return pythoncom.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (float(x), float(y), float(z)))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def same_windows_path(a: Path, b: Path) -> bool:
    import os
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))
