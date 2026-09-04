"""Alias directories: every link is a pure function of the skill set."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from btm_repo_gate.conventions import HUB, VENDOR_LINKS
from btm_repo_gate.repairs import (
    Finding,
    MakeSymlink,
    RemoveLinkFarm,
    RemovePath,
    _relative_target,
)
from btm_repo_gate.snapshot import Absent, LinkFarm, Occupied, Repo, Symlink


def rule_alias(repo: Repo) -> Iterator[Finding]:
    """Every alias is a pure function of the skill set: missing, wrong,
    orphaned, or legacy-shaped is repaired; real content blocks, since
    deleting it would destroy work no derivation can rebuild."""
    if isinstance(repo.links[HUB], Symlink):
        yield Finding(
            "alias",
            str(HUB),
            "hub must be a real directory, not a symlink",
            RemovePath(HUB),
        )
        return  # entries are meaningless through a symlinked hub; next round
    wanted = {
        HUB / skill: _relative_target(HUB / skill, Path(skill)) for skill in repo.skills
    }
    wanted |= {vendor: _relative_target(vendor, HUB) for vendor in VENDOR_LINKS}
    for link, target in sorted(wanted.items()):
        match repo.links.get(link, Absent()):
            case Symlink(found) if found == target:
                pass
            case Symlink(_) | Absent():
                yield Finding(
                    "alias",
                    str(link),
                    f"discovery alias must be a symlink to {target}",
                    MakeSymlink(link, target),
                )
            case LinkFarm():
                yield Finding(
                    "alias",
                    str(link),
                    "a directory of symlinks stands where the alias belongs",
                    RemoveLinkFarm(link),
                )
            case Occupied():
                yield Finding(
                    "alias",
                    str(link),
                    "real content stands where the alias belongs; move it aside",
                )
    # Per-skill kernel links belong to rule_kernel, not this rule.
    managed = {
        link for link in repo.links if link in VENDOR_LINKS or link.parts[0] == HUB.name
    }
    for orphan in sorted(managed - set(wanted) - {HUB}):
        match repo.links[orphan]:
            case Absent():
                pass
            case Symlink(_):
                yield Finding(
                    "alias", str(orphan), "alias names no skill", RemovePath(orphan)
                )
            case LinkFarm():
                yield Finding(
                    "alias", str(orphan), "alias names no skill", RemoveLinkFarm(orphan)
                )
            case Occupied():
                yield Finding(
                    "alias",
                    str(orphan),
                    "names no skill yet holds real content; "
                    "possibly a mislocated skill directory",
                )
