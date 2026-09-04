"""Single definition: a consumer may depend on the kernel, never redefine it."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from btm_repo_gate.conventions import KERNEL
from btm_repo_gate.repairs import Finding, RemovePath
from btm_repo_gate.snapshot import Absent, LinkFarm, Occupied, Repo, Symlink

WORD_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


def _defined_name(line: str, keyword: str) -> str | None:
    """The identifier a top-level `def`/`class` line introduces, else None."""
    if not line.startswith(keyword):
        return None
    end = len(keyword)
    while end < len(line) and line[end] in WORD_CHARS:
        end += 1
    return line[len(keyword) : end] or None


@dataclass(frozen=True, slots=True)
class Kernel:
    """What the kernel defines."""

    functions: frozenset[str]
    classes: frozenset[str]


def kernel_symbols(repo: Repo) -> Kernel:
    """Public top-level defs and classes of the kernel package. Derived, so a
    symbol added there is guarded the moment it exists."""
    functions: set[str] = set()
    classes: set[str] = set()
    for path, text in repo.texts.items():
        # `src/` only: the kernel's own tests name helpers a member may reuse.
        if path.suffix != ".py" or path.parts[:1] != (KERNEL.name,):
            continue
        if "src" not in path.parts:
            continue
        for line in text.split("\n"):
            if name := _defined_name(line, "def "):
                functions.add(name)
            elif name := _defined_name(line, "class "):
                classes.add(name)
    return Kernel(
        frozenset(n for n in functions if not n.startswith("_")),
        frozenset(n for n in classes if not n.startswith("_")),
    )


def redefined_kernel_symbols(text: str, kernel: Kernel) -> Iterator[str]:
    """Defs that shadow a kernel name; skips files with no def/class fast."""
    if "def " not in text and "class " not in text:
        return
    for line in text.split("\n"):
        if (name := _defined_name(line, "def ")) and name in kernel.functions:
            if line[len("def ") + len(name) :].startswith("("):
                yield f"def {name}("
        elif (name := _defined_name(line, "class ")) and name in kernel.classes:
            yield f"class {name}"


def declares_kernel_dependency(manifest: str) -> bool:
    """A `dependencies = [...]` table entry naming btm-corekit; the witness of
    consumer-ship, so prose that mentions the kernel stays a non-consumer."""
    for line_start in _line_starts(manifest):
        line = manifest[line_start:].split("\n", 1)[0]
        head, sep, _ = line.partition("=")
        if sep and head.strip() == "dependencies":
            opener = manifest.find("[", line_start)
            closer = manifest.find("]", opener + 1) if opener != -1 else -1
            return closer != -1 and '"btm-corekit"' in manifest[opener:closer]
    return False


def _line_starts(text: str) -> Iterator[int]:
    position = 0
    while position <= len(text):
        yield position
        next_newline = text.find("\n", position)
        if next_newline == -1:
            return
        position = next_newline + 1


def _kernel_consumers(repo: Repo) -> set[Path]:
    """Directories whose Python may not redefine what they already depend on."""
    return {
        path.parent
        for path, text in repo.texts.items()
        if KERNEL.name not in path.parts
        and path.name == "pyproject.toml"
        and declares_kernel_dependency(text)
    }


def rule_kernel(repo: Repo) -> Iterator[Finding]:
    """The kernel is defined once and wired through manifests. A redefined
    kernel symbol has no repair, since which parts moved is a judgment; a
    legacy `.corekit` symlink inside a skill is removed mechanically."""
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
    # Checks every module of a consumer, not just its console entry.
    roots = _kernel_consumers(repo)
    kernel = kernel_symbols(repo)
    for path in sorted(repo.texts):
        if path.suffix != ".py" or not any(root in path.parents for root in roots):
            continue
        for found in redefined_kernel_symbols(repo.texts[path], kernel):
            yield Finding(
                "kernel",
                str(path),
                f"kernel symbol redefined in a consumer: {found}",
            )
