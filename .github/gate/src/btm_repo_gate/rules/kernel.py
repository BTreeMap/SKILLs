"""Single definition: a consumer may depend on the kernel, never redefine it."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from btm_repo_gate.conventions import KERNEL
from btm_repo_gate.repairs import Finding, RemovePath
from btm_repo_gate.snapshot import Absent, LinkFarm, Occupied, Repo, Symlink

KERNEL_SYMBOLS = re.compile(
    r"^(?:def (?:keywords_of|slugify|band_signal|resolve|eliminate|mint|suffix|"
    r"is_pathlike|tree_bytes|state_root|emit|signal|now_iso|write_atomic|"
    r"read_jsonl|append_jsonl|request_identity|user_agent|polite_params|"
    r"run_cli|jot|recall|pad_body|pad_entries|pad_ids)\(|"
    r"class (?:Exact|Recovered|Ambiguous|NoMatch|CommandError|UpstreamError|"
    r"SessionStore|CustomAgent|Contact|Diagnostic)\b)",
    re.MULTILINE,
)
# The witness of consumer-ship is a declared dependency in a member manifest,
# so a file that merely mentions the kernel in prose stays a non-consumer.
KERNEL_REQUIREMENT = re.compile(
    r"^dependencies\s*=\s*\[[^\]]*\"btm-corekit\"", re.MULTILINE | re.DOTALL
)


def _kernel_consumers(repo: Repo) -> set[Path]:
    """Directories whose Python may not redefine what they already depend on."""
    return {
        path.parent
        for path, text in repo.texts.items()
        if KERNEL.name not in path.parts
        and path.name == "pyproject.toml"
        and KERNEL_REQUIREMENT.search(text)
    }


def rule_kernel(repo: Repo) -> Iterator[Finding]:
    """The kernel is defined once and wired by the manifests. A file that
    redefines a kernel symbol has smuggled a copy back in, and which parts
    moved is a judgment, so that has no repair. A workspace member reaches
    the kernel through its manifest alone, so a dotted `.corekit` symlink
    inside a skill is a legacy remnant, removed mechanically."""
    for skill in sorted(repo.skills):
        link = Path(skill) / KERNEL.name
        match repo.links.get(link, Absent()):
            case Absent():
                pass
            case Symlink(_):
                yield Finding(
                    "kernel",
                    str(link),
                    "kernel symlink is legacy; the member manifest declares "
                    "the dependency",
                    RemovePath(link),
                )
            case LinkFarm() | Occupied():
                yield Finding(
                    "kernel",
                    str(link),
                    "real content stands at the legacy kernel-symlink path; "
                    "move it aside",
                )
    # A member's modules are covered, not just its console entry, so moving a
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
