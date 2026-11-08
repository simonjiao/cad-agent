"""Read-only real AutoCAD 2019 COM preflight, run with Windows venv Python."""
from __future__ import annotations

import json
import sys
from com_common import attach, release


def main() -> int:
    pythoncom, app, version = attach()
    try:
        try:
            doc = app.ActiveDocument
            doc_name = str(doc.Name)
            doc_path = str(doc.FullName)
            entity_count = int(doc.ModelSpace.Count)
        except Exception as exc:
            raise RuntimeError("AutoCAD is attached but no readable active document is available") from exc
        print(json.dumps({"ok": True, "version": version,
                          "active_document": doc_name, "full_path": doc_path,
                          "model_space_count": entity_count}, ensure_ascii=False, indent=2))
    finally:
        release(pythoncom)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"COM TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
