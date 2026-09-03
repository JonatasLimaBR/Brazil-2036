from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

_PLACEHOLDER = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class MissingPlaceholder(KeyError):
    pass


def render(sql: str, values: Mapping[str, str]) -> str:
    missing: set[str] = set()

    def _sub(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            missing.add(name)
            return match.group(0)
        return str(values[name])

    result = _PLACEHOLDER.sub(_sub, sql)
    if missing:
        raise MissingPlaceholder(f"unresolved placeholders: {sorted(missing)}")
    return result


def render_file(path: str | Path, values: Mapping[str, str]) -> str:
    return render(Path(path).read_text(encoding="utf-8"), values)
