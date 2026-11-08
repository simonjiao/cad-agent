"""Assert actual AutoCAD 2019 geometries and persisted DWG after Codex edit."""
from __future__ import annotations

import argparse
import json
from math import isclose
import sys
from com_common import (
    BASELINE, BASELINE_HASH, WORKING, attach, release,
    same_windows_path, sha256,
)


def close_to(a, b) -> bool:
    return isclose(float(a), float(b), abs_tol=1e-5)


def xyz_equal(a, b) -> bool:
    return all(close_to(a[i], b[i]) for i in range(3))


def read_entities(doc):
    items = []
    for entity in doc.ModelSpace:
        kind = str(entity.ObjectName)
        layer = str(entity.Layer)
        if kind.endswith("AcDbLine"):
            items.append({"kind": "line", "layer": layer,
                          "start": tuple(entity.StartPoint), "end": tuple(entity.EndPoint)})
        elif kind.endswith("AcDbCircle"):
            items.append({"kind": "circle", "layer": layer,
                          "center": tuple(entity.Center), "radius": float(entity.Radius)})
        else:
            items.append({"kind": kind, "layer": layer})
    return items


def exact_line(entity, p1, p2, layer):
    if entity["kind"] != "line" or entity["layer"] != layer:
        return False
    return ((xyz_equal(entity["start"], p1) and xyz_equal(entity["end"], p2)) or
            (xyz_equal(entity["start"], p2) and xyz_equal(entity["end"], p1)))


def exact_circle(entity, center, radius, layer):
    return entity["kind"] == "circle" and entity["layer"] == layer and \
        xyz_equal(entity["center"], center) and close_to(entity["radius"], radius)


def validate(entities):
    base = [e for e in entities if e["layer"] == "AI_BASE"]
    extra = [e for e in entities if e["layer"] == "AI_ADDED"]
    expected_lines = [((0, 0, 0), (100, 0, 0)), ((100, 0, 0), (100, 60, 0)),
                      ((100, 60, 0), (0, 60, 0)), ((0, 60, 0), (0, 0, 0))]
    failures = []
    if len(base) != 5:
        failures.append(f"AI_BASE objects: {len(base)} expected 5")
    for p1, p2 in expected_lines:
        if sum(exact_line(e, p1, p2, "AI_BASE") for e in base) != 1:
            failures.append(f"Missing or duplicate base line {p1}->{p2}")
    if sum(exact_circle(e, (50, 30, 0), 10, "AI_BASE") for e in base) != 1:
        failures.append("Baseline circle changed or missing")
    if len(extra) != 2:
        failures.append(f"AI_ADDED objects: {len(extra)} expected 2")
    if sum(exact_line(e, (0, 30, 0), (100, 30, 0), "AI_ADDED") for e in extra) != 1:
        failures.append("AI_ADDED centre line not found at expected coordinates")
    if sum(exact_circle(e, (50, 30, 0), 15, "AI_ADDED") for e in extra) != 1:
        failures.append("AI_ADDED circle not found at expected centre/radius")
    if len(entities) != 7:
        failures.append(f"ModelSpace total: {len(entities)} expected 7")
    return failures


def main():
    parser = argparse.ArgumentParser(description="Validate COM entities and saved DWG")
    parser.add_argument("--reopen", action="store_true", help="Close saved test drawing and reopen to confirm persistence")
    args = parser.parse_args()
    if not WORKING.exists() or not BASELINE.exists() or not BASELINE_HASH.exists():
        raise RuntimeError("Demo files missing; first run create_demo.py")
    if sha256(BASELINE) != BASELINE_HASH.read_text(encoding="ascii").strip():
        raise RuntimeError("Baseline DWG changed unexpectedly. Stop testing and investigate.")
    pythoncom, app, version = attach()
    try:
        doc = app.ActiveDocument
        if not same_windows_path(WORKING, __import__("pathlib").Path(str(doc.FullName))):
            raise RuntimeError(f"Wrong active drawing: {doc.FullName}; expected {WORKING}")
        if not bool(doc.Saved):
            raise RuntimeError("Test drawing is not saved. Save via MCP before validation.")
        # Validate saved DWG by closing and reopening it on the user's request.
        if args.reopen:
            doc.Close(False)
            doc = app.Documents.Open(str(WORKING))
            doc.Activate()
        all_entities = read_entities(doc)
        failures = validate(all_entities)
        print(json.dumps({"ok": not failures, "cad_version": version,
                          "working_dwg": str(WORKING), "reopened": args.reopen,
                          "model_count": len(all_entities),
                          "layers": sorted(set(e["layer"] for e in all_entities)),
                          "baseline_unchanged": True, "failures": failures},
                         ensure_ascii=False, indent=2))
        return 0 if not failures else 2
    finally:
        release(pythoncom)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"VERIFY DEMO FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
