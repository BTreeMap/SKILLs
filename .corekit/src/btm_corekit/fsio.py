"""Filesystem effects: state placement, sizing, atomic writes, JSONL containers."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def state_root(skill: str) -> Path:
    """Durable-state home for one skill, per repository convention."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    else:
        base = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
    return Path(base) / "btm-skills" / skill


def tree_bytes(path: Path) -> int:
    """Total size of the regular files under a directory."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def write_atomic(path: Path, text: str) -> None:
    """Encode first, write a sibling temp file, fsync, then os.replace().

    The destination only ever moves from one complete file to another;
    permission bits survive the swap.
    """
    data = text.encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            os.chmod(tmp_path, stat.S_IMODE(path.stat().st_mode))
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def count_lines(path: Path) -> int:
    """Records a JSONL file holds, counted without decoding one."""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def append_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    """One record is a batch of one."""
    payload = "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload)
