"""One session layout for every session-keeping skill."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict

from btm_corekit.records.models import M, Model, NonEmpty, dump, parse_model
from btm_corekit.report.channels import signal
from btm_corekit.report.errors import CommandError
from btm_corekit.store.fsio import remove_tree, state_root, tree_bytes, write_atomic
from btm_corekit.store.identifiers import (
    band_signal,
    eliminate,
    is_pathlike,
    mint,
    resolve,
)


class Link(Model):
    """One session of another skill this session draws on: the skill, the
    session's identifier, and the directory it lives in."""

    skill: NonEmpty
    session: NonEmpty
    path: NonEmpty


class Tagged(Model):
    """What every session meta carries beside its own fields: a free project
    name, set at init, that groups sessions across skills, and the sessions
    of other skills it links. A member's meta model subclasses this."""

    project: NonEmpty | None = None
    links: tuple[Link, ...] = ()

    def with_link(self, link: Link) -> Self:
        """One link per linked skill: relinking replaces the earlier one."""
        kept = tuple(held for held in self.links if held.skill != link.skill)
        return self.with_(links=(*kept, link))


class Tags(Tagged):
    """The tags alone, read from any member's meta; its own fields ignored."""

    model_config = ConfigDict(frozen=True, extra="ignore")


@dataclass(frozen=True, slots=True)
class Created:
    """A fresh session: its identifier (or the path given) and directory."""

    name: str
    directory: Path


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

    def directory(self, ref: str) -> Path:
        """`dir_of`, then the marker must exist: the session is real."""
        found = self.dir_of(ref)
        if not (found / self.marker).is_file():
            raise CommandError(f"no session at {found}: {self.hint}")
        return found

    def create(self, ref: str) -> Created:
        """A path stands as given; keywords mint an identifier under the root.
        An existing marker refuses, so creation never overwrites."""
        if is_pathlike(ref):
            directory = Path(ref).expanduser()
            name = str(directory)
        else:
            name = mint(ref.split())
            if advice := band_signal(name.rsplit("-", 1)[0]):
                signal(advice)
            directory = self.root() / name
        if (directory / self.marker).exists():
            raise CommandError(f"session already exists at {directory}")
        return Created(name, directory)

    def meta_path(self, directory: Path) -> Path:
        return directory / self.marker

    def read_meta(self, directory: Path, model: type[M]) -> M:
        """The marker file, decoded into the record the member declares."""
        path = self.meta_path(directory)
        if not path.is_file():
            raise CommandError(f"no session at {directory}: {self.hint}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise CommandError(f"unreadable {path}: {err}") from err
        return parse_model(model, raw, str(path))

    def write_meta(self, directory: Path, meta: BaseModel) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        write_atomic(
            self.meta_path(directory),
            json.dumps(dump(meta), indent=2, ensure_ascii=False) + "\n",
        )

    def lore(self) -> Path:
        """The skill's cross-session pad, beside its sessions."""
        return state_root(self.skill) / "lore"

    def project_of(self, directory: Path) -> str | None:
        """The project a session's meta names. A listing is a view, so an
        unreadable meta lists with none and a signal, never a refusal."""
        if not self.meta_path(directory).is_file():
            return None
        try:
            return self.read_meta(directory, Tags).project
        except CommandError as err:
            signal(f"listing {directory.name} without its project: {err}")
            return None

    def clean(
        self, ref: str | None, remove_all: bool, project: str | None = None
    ) -> dict[str, Any]:
        """List sessions with sizes and projects, `project` keeping only its
        own; remove one; or remove them all, reporting bytes freed. Every
        removal demands the marker, never an arbitrary tree: `--all` removes
        the root only when every entry under it is a session."""
        root = self.root()
        if remove_all and ref:
            raise CommandError("pass a session or --all, one of the two")
        if project is not None and (remove_all or ref):
            raise CommandError("--project filters the listing; pass it alone")
        if remove_all:
            return self._remove_all(root)
        if ref is None:
            entries = sorted(root.iterdir()) if root.is_dir() else []
            listing = [
                {
                    "session": entry.name,
                    "project": self.project_of(entry),
                    "bytes": tree_bytes(entry),
                }
                for entry in entries
                if entry.is_dir()
            ]
            return {
                "sessions_root": str(root),
                "sessions": [
                    row for row in listing if project in (None, row["project"])
                ],
                "next": "pass a session identifier or --all to remove and free space",
            }
        target = self.dir_of(ref)
        if not (target / self.marker).is_file():
            raise CommandError(
                f"{target} holds no session ({self.marker} absent); refusing to remove"
            )
        return remove_tree(target)

    def _remove_all(self, root: Path) -> dict[str, Any]:
        """All or nothing: every entry under the root must carry the marker,
        or nothing is removed and the strays are named."""
        if not root.is_dir():
            return remove_tree(root)
        strays = sorted(
            entry.name
            for entry in root.iterdir()
            if not (entry / self.marker).is_file()
        )
        if strays:
            raise CommandError(
                f"{root} holds entries without {self.marker}: {', '.join(strays)}; "
                "refusing to remove anything until they are moved aside"
            )
        return remove_tree(root)


LIT_REVIEW_SESSIONS = SessionStore(
    "lit-review", marker="protocol.json", hint="run lit-review init first"
)
LIT_REVIEW_CORPUS = "papers.jsonl"
"""lit-review's session layout, the one cross-member contract: lit-review
writes its corpus here and peer-review links to it, so neither may restate
where it lives."""
