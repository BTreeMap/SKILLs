"""An append-only, stamped JSONL event log with a size backstop. A member's
`apply` decides what may enter; this class decides how it is written and
read back. Reading is O(events); appending is O(new) plus one line count."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from btm_corekit.clock import now_iso
from btm_corekit.errors import CommandError
from btm_corekit.fsio import append_jsonl, count_lines, read_jsonl

MAX_EVENTS = 2000  # runaway backstop; a real session stays well under it


@dataclass(frozen=True, slots=True)
class EventLog:
    path: Path
    hint: str = "run init first"
    cap: int = MAX_EVENTS

    def exists(self) -> bool:
        return self.path.is_file()

    def touch(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    def read(self) -> list[dict[str, Any]]:
        if not self.exists():
            raise CommandError(f"no session at {self.path.parent}: {self.hint}")
        return read_jsonl(self.path)

    def count(self) -> int:
        return count_lines(self.path)

    def append(
        self, events: Iterable[Mapping[str, Any]], *, held: int | None = None
    ) -> None:
        """Stamp each event with `t` and append; the cap counts the whole log.
        A caller that replayed the log passes its event count as `held`, so
        the file is read once per command."""
        batch = list(events)
        held = self.count() if held is None else held
        if held + len(batch) > self.cap:
            raise CommandError(
                f"ledger would exceed {self.cap} events ({held} held, "
                f"{len(batch)} offered)"
            )
        stamp = now_iso()
        append_jsonl(self.path, [{"t": stamp, **event} for event in batch])
