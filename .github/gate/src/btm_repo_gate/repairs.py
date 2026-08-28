"""What a finding may do about itself: the closed repair set, and Finding."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WriteText:
    path: Path
    text: str

    def apply(self, root: Path) -> None:
        (root / self.path).write_text(self.text)


@dataclass(frozen=True, slots=True)
class MakeSymlink:
    """Constructed only against `Absent` or `Symlink` states; if the tree
    moved since the snapshot and real content now stands here, leave it for
    the next round's fresh audit rather than destroy it."""

    path: Path
    target: str

    def apply(self, root: Path) -> None:
        link = root / self.path
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            return
        link.symlink_to(self.target)


@dataclass(frozen=True, slots=True)
class RemovePath:
    """Removes a symlink. Anything else is real content, which no repair may
    destroy, so it is left standing for the next audit to report."""

    path: Path

    def apply(self, root: Path) -> None:
        target = root / self.path
        if target.is_symlink():
            target.unlink()


@dataclass(frozen=True, slots=True)
class RemoveLinkFarm:
    """Removes a directory whose children are all symlinks (the legacy alias
    layout). Rebuilding such a directory is pure derivation, so deleting it
    loses nothing; a directory holding any real file is refused."""

    path: Path

    def apply(self, root: Path) -> None:
        farm = root / self.path
        if farm.is_symlink() or not farm.is_dir():
            return
        children = list(farm.iterdir())
        if any(not child.is_symlink() for child in children):
            return
        for child in children:
            child.unlink()
        farm.rmdir()


Repair = WriteText | MakeSymlink | RemovePath | RemoveLinkFarm


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    path: str
    message: str
    repair: Repair | None = None

    def render(self) -> str:
        mark = "fixable " if self.repair is not None else "blocking"
        return f"{mark} {self.rule:<14} {self.path}: {self.message}"


def _relative_target(link: Path, dest: Path) -> str:
    """The symlink target from `link` to `dest`, both repo-relative.

    Pure path arithmetic, so an alias target can never disagree with the
    location it is derived from, and a link always names a destination
    distinct from itself.
    """
    assert link != dest, f"self-link: {link}"
    return os.path.relpath(dest, link.parent)
