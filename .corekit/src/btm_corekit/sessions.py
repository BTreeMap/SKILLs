"""One session layout for every session-keeping skill."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from btm_corekit.channels import signal
from btm_corekit.errors import CommandError
from btm_corekit.fsio import state_root, tree_bytes
from btm_corekit.identifiers import eliminate, is_pathlike, resolve


@dataclass(frozen=True, slots=True)
class SessionStore:
    """Sessions under the skill's state root; `marker` witnesses a session,
    `hint` names the command that creates one."""

    skill: str
    marker: str
    hint: str

    def root(self) -> Path:
        return state_root(self.skill) / "sessions"

    def ids(self) -> list[str]:
        root = self.root()
        if not root.exists():
            return []
        return sorted(entry.name for entry in root.iterdir() if entry.is_dir())

    def dir_of(self, ref: str) -> Path:
        """A path argument stands as given; anything else resolves against
        `ids()`, rendering the recovery signal."""
        if is_pathlike(ref):
            return Path(ref).expanduser()
        full, note = eliminate(resolve(ref, self.ids()), ref, "session", hint=self.hint)
        if note:
            signal(note)
        return self.root() / full

    def clean(self, ref: str | None, remove_all: bool) -> dict[str, Any]:
        """List sessions with sizes, or remove one session or the whole root,
        reporting bytes freed. Removal demands the marker: never an arbitrary
        tree."""
        root = self.root()
        if remove_all and ref:
            raise CommandError("pass a session or --all, one of the two")
        if remove_all:
            if not root.is_dir():
                return {"removed": None, "bytes_freed": 0}
            freed = tree_bytes(root)
            shutil.rmtree(root)
            return {"removed": str(root), "bytes_freed": freed}
        if ref is None:
            listing = (
                [
                    {"session": entry.name, "bytes": tree_bytes(entry)}
                    for entry in sorted(root.iterdir())
                    if entry.is_dir()
                ]
                if root.is_dir()
                else []
            )
            return {
                "sessions_root": str(root),
                "sessions": listing,
                "next": "pass a session identifier or --all to remove and free space",
            }
        target = self.dir_of(ref)
        if not (target / self.marker).is_file():
            raise CommandError(
                f"{target} holds no session ({self.marker} absent); refusing to remove"
            )
        freed = tree_bytes(target)
        shutil.rmtree(target)
        return {"removed": str(target), "bytes_freed": freed}
