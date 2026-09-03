from __future__ import annotations

import json
import sys
from pathlib import Path

from api.main import app

DEST = Path(__file__).resolve().parents[1] / "openapi" / "openapi.json"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    DEST.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
