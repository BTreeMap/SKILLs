"""Single definition: a consumer may depend on the kernel, never redefine it."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from btm_repo_gate.conventions import KERNEL
from btm_repo_gate.repairs import Finding, MakeSymlink, RemovePath, _relative_target
from btm_repo_gate.snapshot import Absent, LinkFarm, Occupied, Repo, Symlink

KERNEL_SYMBOLS = re.compile(
    r"^(?:def (?:keywords_of|slugify|band_signal|resolve|eliminate|mint|suffix|"
    r"is_pathlike|tree_bytes|state_root)\(|"
    r"class (?:Exact|Recovered|Ambiguous|NoMatch|CommandError)\b)",
    re.MULTILINE,
)
# The witness of consumer-ship is a declared dependency, so a file that merely
# mentions the kernel in prose stays a non-consumer. A workspace member
# declares it in its manifest; a PEP 723 script declares it in its header.
KERNEL_DEPENDENCY = re.compile(r'^#\s*dependencies\s*=.*"btm-corekit"', re.MULTILINE)
KERNEL_REQUIREMENT = re.compile(
    r"^dependencies\s*=\s*\[[^\]]*\"btm-corekit\"", re.MULTILINE | re.DOTALL
)


def _kernel_consumers(repo: Repo) -> set[Path]:
    """Directories whose Python may not redefine what they already depend on."""
    roots: set[Path] = set()
    for path, text in repo.texts.items():
        if KERNEL.name in path.parts:
            continue
        if path.name == "pyproject.toml" and KERNEL_REQUIREMENT.search(text):
            roots.add(path.parent)
        elif path in repo.entry_points and KERNEL_DEPENDENCY.search(text):
            roots.add(Path(path.parts[0]))
    return roots


def rule_kernel(repo: Repo) -> Iterator[Finding]:
    """The kernel is defined once and wired by derivation. A file that
    redefines a kernel symbol has smuggled a copy back in, and which parts
    moved is a judgment, so that has no repair. A PEP 723 consumer script
    (one whose header names btm-corekit) still reaches the kernel through a
    dotted symlink, a pure function of consumer-ship, so that is repaired; a
    workspace member states the dependency in its manifest and needs none."""
    consumers = {
        path.parts[0]
        for path in repo.entry_points
        if KERNEL_DEPENDENCY.search(repo.texts[path])
    }
    for skill in sorted(repo.skills):
        link = Path(skill) / KERNEL.name
        target = _relative_target(link, KERNEL)
        match repo.links.get(link, Absent()), skill in consumers:
            case (Symlink(found), True) if found == target:
                pass
            case (Symlink(_) | Absent(), True):
                yield Finding(
                    "kernel",
                    str(link),
                    f"consumer skill needs a kernel symlink to {target}",
                    MakeSymlink(link, target),
                )
            case (Absent(), False):
                pass
            case (Symlink(_), False):
                yield Finding(
                    "kernel",
                    str(link),
                    "kernel symlink without a consumer script",
                    RemovePath(link),
                )
            case (LinkFarm() | Occupied(), _):
                yield Finding(
                    "kernel",
                    str(link),
                    "real content stands where the kernel symlink belongs; "
                    "move it aside",
                )
    # A member's modules are covered, not just its entry point, so moving a
    # copy of the kernel one import deeper does not escape the check.
    roots = _kernel_consumers(repo)
    for path in sorted(repo.texts):
        if path.suffix != ".py" or not any(root in path.parents for root in roots):
            continue
        for found in KERNEL_SYMBOLS.finditer(repo.texts[path]):
            yield Finding(
                "kernel",
                str(path),
                f"kernel symbol redefined in a consumer: {found.group(0)}",
            )
