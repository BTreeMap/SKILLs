"""Session filesystem: where a ledger lives, how it is read, appended, described."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from btm_corekit import CommandError, eliminate, is_pathlike, resolve, state_root
from btm_ponder.ledger import replay
from btm_ponder.report import signal
from btm_ponder.state import Open
from btm_ponder.views import counts_of, yield_table


def sessions_root() -> Path:
    return state_root("ponder") / "sessions"


def session_ids() -> list[str]:
    root = sessions_root()
    if not root.exists():
        return []
    return sorted(entry.name for entry in root.iterdir() if entry.is_dir())


def resolved_session(ref: str) -> Path:
    """Eliminate a session Resolution at the shell, rendering its signal."""
    full, note = eliminate(
        resolve(ref, session_ids()),
        ref,
        "session",
        hint="open with --question creates one",
    )
    if note:
        signal(note)
    return sessions_root() / full


def session_dir(ref: str) -> Path:
    if is_pathlike(ref):
        return Path(ref).expanduser()
    return resolved_session(ref)


def ledger_path(directory: Path) -> Path:
    return directory / "ledger.jsonl"


def read_events(directory: Path) -> list[dict[str, Any]]:
    path = ledger_path(directory)
    if not path.exists():
        raise CommandError(f"no session at {directory}; open with --question creates")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def append_events(directory: Path, admitted: list[dict[str, Any]]) -> None:
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    payload = "".join(
        json.dumps({"t": stamp, **raw}, ensure_ascii=False) + "\n" for raw in admitted
    )
    with ledger_path(directory).open("a", encoding="utf-8") as handle:
        handle.write(payload)


def read_meta(directory: Path) -> dict[str, Any]:
    path = directory / "session.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def write_meta(directory: Path, meta: dict[str, Any]) -> None:
    """Write session metadata through a temporary file, so a reader sees it whole."""
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=directory, delete=False, encoding="utf-8"
    ) as handle:
        json.dump(meta, handle, indent=2, ensure_ascii=False)
    Path(handle.name).replace(directory / "session.json")
    ledger_path(directory).touch()


def orient(directory: Path) -> dict[str, Any]:
    """The re-orientation payload: everything a resumed agent needs first."""
    events = read_events(directory)
    ledger = replay(events)
    return {
        "session": directory.name,
        "question": read_meta(directory).get("question"),
        "focus": read_meta(directory).get("focus"),
        "counts": counts_of(ledger),
        "open": [
            {"id": leaf_id, "q": leaf.question}
            for leaf_id, leaf in ledger.leaves.items()
            if isinstance(leaf.state, Open)
        ],
        "swept": ledger.swept,
        "yield": yield_table(events),
    }
