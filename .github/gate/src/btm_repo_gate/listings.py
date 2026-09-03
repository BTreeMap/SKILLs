"""The generated skill listings in README.md and AGENTS.md."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Listing:
    """A contiguous run of per-skill entries inside a document, with the text
    that surrounds it, so rebuilding cannot disturb anything else."""

    before: tuple[str, ...]
    entries: tuple[tuple[str, tuple[str, ...]], ...]  # (skill, its lines)
    after: tuple[str, ...]

    @property
    def named(self) -> list[str]:
        return [name for name, _ in self.entries]

    def sorted_text(self) -> str:
        ordered = sorted(self.entries, key=lambda entry: entry[0])
        body = [line for _, lines in ordered for line in lines]
        return "\n".join([*self.before, *body, *self.after])


def _readme_listing(text: str) -> Listing | None:
    """The rows of the skills table, one line each, keyed by their link text."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if not line.startswith("| Skill |"):
            continue
        start = index + 2  # past the header and its `| --- |` separator
        end = start
        while end < len(lines) and lines[end].startswith("| ["):
            end += 1
        entries = tuple(
            (_between(lines[row], "[", "]"), (lines[row],)) for row in range(start, end)
        )
        return Listing(tuple(lines[:start]), entries, tuple(lines[end:]))
    return None


def _agents_listing(text: str) -> Listing | None:
    """The bullet list under `Current skills:`, whose entries wrap onto
    indented continuation lines."""
    lines = text.split("\n")
    try:
        anchor = lines.index("Current skills:")
    except ValueError:
        return None
    start = anchor
    while start < len(lines) and not lines[start].startswith("* "):
        start += 1
    entries: list[tuple[str, list[str]]] = []
    row = start
    while row < len(lines):
        line = lines[row]
        if line.startswith("* "):
            name = _between(line, "`", "`").rstrip("/")
            entries.append((name, [line]))
        elif entries and line.startswith("  ") and line.strip():
            entries[-1][1].append(line)
        else:
            break
        row += 1
    frozen = tuple((name, tuple(body)) for name, body in entries)
    return Listing(tuple(lines[:start]), frozen, tuple(lines[row:]))


def _between(line: str, opener: str, closer: str) -> str:
    """Text inside the first non-empty `opener ... closer` pair, else the line."""
    start = line.find(opener)
    end = line.find(closer, start + 1) if start != -1 else -1
    return line[start + 1 : end] if end > start + 1 else line


# Pair each document with its extractor; do not infer one from another.
LISTINGS: tuple[tuple[Path, Callable[[str], Listing | None]], ...] = (
    (Path("README.md"), _readme_listing),
    (Path("AGENTS.md"), _agents_listing),
)
