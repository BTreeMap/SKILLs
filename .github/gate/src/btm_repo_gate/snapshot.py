"""An immutable reading of the repository: every rule is a function of it."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from btm_repo_gate.conventions import (
    HUB,
    KERNEL,
    MARKETPLACE,
    PLUGIN_MANIFEST,
    PRUNED_DIRS,
    TEXT_SUFFIXES,
    VENDOR_LINKS,
)


@dataclass(frozen=True, slots=True)
class Symlink:
    target: str


@dataclass(frozen=True, slots=True)
class Absent:
    pass


@dataclass(frozen=True, slots=True)
class LinkFarm:
    """A real directory of only symlinks: rebuildable, so mechanically removable."""


@dataclass(frozen=True, slots=True)
class Occupied:
    """A file, or a directory holding real content: never mechanically removable."""


LinkState = Symlink | Absent | LinkFarm | Occupied


def _link_state(path: Path) -> LinkState:
    if path.is_symlink():
        return Symlink(os.readlink(path))
    if path.is_dir():
        only_links = all(child.is_symlink() for child in path.iterdir())
        return LinkFarm() if only_links else Occupied()
    return Occupied() if path.exists() else Absent()


@dataclass(frozen=True, slots=True)
class Parsed:
    doc: dict[str, Any]  # shallowly immutable; rules copy before rewriting


@dataclass(frozen=True, slots=True)
class Unreadable:
    reason: str


ManifestState = Parsed | Unreadable | Absent


def _manifest_state(path: Path) -> ManifestState:
    if not path.is_file():
        return Absent()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return Unreadable(str(error))
    if not isinstance(doc, dict):
        return Unreadable("top level is not an object")
    return Parsed(doc)


@dataclass(frozen=True, slots=True)
class Repo:
    """An immutable reading of the repository; every rule is a pure function of it."""

    skills: frozenset[str]
    texts: Mapping[Path, str]  # repo-relative path to contents
    links: Mapping[Path, LinkState]  # hub, its entries, and the vendor paths
    manifests: Mapping[Path, ManifestState]


def snapshot(root: Path) -> Repo:
    """Parse a directory into the repository this program knows how to judge.
    Every top-level directory that is neither dotted nor the `skills/` hub is
    a skill directory (AGENTS.md's reserved namespace), read from the tree.
    """
    if not (root / "AGENTS.md").is_file():
        raise SystemExit(f"not a skills repository: {root}/AGENTS.md is missing")
    skills = frozenset(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir()
        and not entry.is_symlink()
        and not entry.name.startswith(".")
        and entry.name != HUB.name
    )
    texts: dict[Path, str] = {}
    for parent, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [name for name in dirnames if name not in PRUNED_DIRS]
        here = Path(parent)
        for name in filenames:
            path = here / name
            if path.is_symlink() or path.suffix not in TEXT_SUFFIXES:
                continue
            relative = path.relative_to(root)
            texts[relative] = path.read_text(encoding="utf-8", errors="replace")
    links: dict[Path, LinkState] = {HUB: _link_state(root / HUB)}
    for vendor in VENDOR_LINKS:
        links[vendor] = _link_state(root / vendor)
    for skill in skills:
        kernel_link = Path(skill) / KERNEL.name
        links[kernel_link] = _link_state(root / kernel_link)
    # Hub entries are read only from a real hub dir; a symlink could name another tree.
    if isinstance(links[HUB], LinkFarm | Occupied):
        present = {entry.name for entry in (root / HUB).iterdir()}
    else:
        present = set()
    for name in skills | present:
        links[HUB / name] = _link_state(root / HUB / name)
    manifests = {
        path: _manifest_state(root / path) for path in (MARKETPLACE, PLUGIN_MANIFEST)
    }
    return Repo(skills, texts, links, manifests)
