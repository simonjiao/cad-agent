"""Generate two isolated AutoCAD 2019 test DWGs; never writes outside ./work."""
from __future__ import annotations

import argparse
import shutil
import sys
from com_common import (
    BASELINE, BASELINE_HASH, WORK, WORKING,
    attach, point, release, sha256,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a separate, small CAD integration demo")
    parser.add_argument("--reset", action="store_true", help="Delete ONLY existing demo files")
    opts = parser.parse_args()
    WORK.mkdir(exist_ok=True)
    targets = (BASELINE, WORKING, BASELINE_HASH)
    existing = [str(p) for p in targets if p.exists()]
    if existing and not opts.reset:
        raise RuntimeError("Refusing to overwrite demo files: " + ", ".join(existing)
                           + ". To reset only these files, use --reset after closing them in AutoCAD.")
    pythoncom, app, version = attach()
    try:
        # Check drawing isn't active before destroying a prior test on --reset.
        for document in app.Documents:
            full = str(document.FullName or "")
            if full and any(full.lower() == str(p).lower() for p in (BASELINE, WORKING)):
                raise RuntimeError("Close the existing demo DWGs in AutoCAD before --reset")
        if opts.reset:
            for p in targets:
                p.unlink(missing_ok=True)
        doc = app.Documents.Add()
        try:
            layer = doc.Layers.Add("AI_BASE")
            layer.Color = 7
            segments = [((0, 0), (100, 0)), ((100, 0), (100, 60)),
                        ((100, 60), (0, 60)), ((0, 60), (0, 0))]
            for (x1, y1), (x2, y2) in segments:
                entity = doc.ModelSpace.AddLine(point(x1, y1), point(x2, y2))
                entity.Layer = "AI_BASE"
            circle = doc.ModelSpace.AddCircle(point(50, 30), 10.0)
            circle.Layer = "AI_BASE"
            doc.SaveAs(str(BASELINE))
        finally:
            # Only the newly created demo document is closed.
            doc.Close(False)
        shutil.copy2(BASELINE, WORKING)
        BASELINE_HASH.write_text(sha256(BASELINE) + "\n", encoding="ascii")
        doc2 = app.Documents.Open(str(WORKING))
        doc2.Activate()
        print(f"AutoCAD {version} | created baseline and working copy")
        print(f"Baseline: {BASELINE}")
        print(f"Working : {WORKING} (active in AutoCAD)")
        print(f"Model-space objects: {int(doc2.ModelSpace.Count)} expected 5")
        if int(doc2.ModelSpace.Count) != 5:
            raise AssertionError("Demo creation count mismatch; inspect current AutoCAD template")
    finally:
        release(pythoncom)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"CREATE DEMO FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
