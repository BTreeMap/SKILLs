"""SKILL.md headers: spec fields in canonical order."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from btm_repo_gate.conventions import (
    DESCRIPTION_LIMIT,
    SPEC_FIELDS,
    split_frontmatter,
)
from btm_repo_gate.repairs import Finding, WriteText
from btm_repo_gate.snapshot import Repo


def rule_skill_layout(repo: Repo) -> Iterator[Finding]:
    for skill in sorted(repo.skills):
        if Path(skill, "SKILL.md") not in repo.texts:
            yield Finding(
                "skill-layout",
                skill,
                "top-level directories are the reserved skill namespace, so this "
                "needs a SKILL.md or belongs in a dotted directory",
            )


def rule_frontmatter(repo: Repo) -> Iterator[Finding]:
    """Frontmatter facts split by who can settle them: `name`, `license`, and
    field order are total functions of the skill and the spec, so drift is
    repaired in one write per file; descriptions and non-spec fields need a
    person."""
    for skill in sorted(repo.skills):
        document = Path(skill, "SKILL.md")
        text = repo.texts.get(document)
        if text is None:
            continue  # rule_skill_layout owns the missing-file case
        where = str(document)
        header = split_frontmatter(text)
        if header is None:
            yield Finding("frontmatter", where, "no YAML frontmatter")
            continue
        try:
            fields = yaml.safe_load(header[0]) or {}
        except yaml.YAMLError as error:
            yield Finding("frontmatter", where, f"unparseable frontmatter: {error}")
            continue
        if not isinstance(fields, dict):
            yield Finding("frontmatter", where, "frontmatter is not a mapping")
            continue
        yield from _frontmatter_judgments(where, fields)
        normalized = _canonical_header(skill, fields, header[0])
        if normalized is not None:
            new_header, reasons = normalized
            repaired = f"---\n{new_header}\n---\n{text[header[1] :]}"
            yield Finding(
                "frontmatter",
                where,
                "; ".join(reasons),
                WriteText(document, repaired),
            )


def _frontmatter_judgments(where: str, fields: dict[str, Any]) -> Iterator[Finding]:
    unknown = [name for name in fields if name not in SPEC_FIELDS]
    if unknown:
        yield Finding(
            "frontmatter",
            where,
            f"non-spec fields {unknown}; record such hints under metadata",
        )
    description = fields.get("description") or ""
    if not description:
        yield Finding("frontmatter", where, "description is required")
    elif len(description) > DESCRIPTION_LIMIT:
        yield Finding(
            "frontmatter",
            where,
            f"description is {len(description)} characters, over {DESCRIPTION_LIMIT}",
        )


def _header_segments(header: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Split a frontmatter block into (top-level key, its exact lines) runs.

    Editing at segment granularity preserves every untouched field byte for
    byte, folded block scalars included, which a YAML re-dump would not.
    """
    segments: list[tuple[str, list[str]]] = []
    for line in header.split("\n"):
        if line[:1] not in ("", " ", "\t", "#") and ":" in line:
            segments.append((line.split(":", 1)[0].strip(), [line]))
        elif segments:
            segments[-1][1].append(line)
        else:
            segments.append(("", [line]))  # leading non-field text, kept opaque
    return tuple((key, tuple(body)) for key, body in segments)


def _canonical_header(
    skill: str, fields: dict[str, Any], header: str
) -> tuple[str, list[str]] | None:
    """The header with `name`, `license`, and field order made canonical, or
    `None` when it already is. A field whose value is right keeps its exact
    original text; only wrong values are rewritten, so the repair diff is
    minimal."""
    segments = list(_header_segments(header))
    reasons: list[str] = []

    def force(key: str, line: str, why: str) -> None:
        nonlocal segments
        if any(k == key for k, _ in segments):
            segments = [(k, (line,)) if k == key else (k, body) for k, body in segments]
        else:
            segments.append((key, (line,)))
        reasons.append(why)

    if fields.get("name") != skill:
        force("name", f"name: {skill}", f"name set to {skill!r}")
    if fields.get("license") != "MIT":
        force("license", "license: MIT", "license set to MIT")
    rank = {field: index for index, field in enumerate(SPEC_FIELDS)}
    ordered = sorted(
        segments,
        key=lambda segment: -1 if segment[0] == "" else rank.get(segment[0], len(rank)),
    )
    if ordered != segments:
        segments = ordered
        reasons.append("fields reordered canonically")
    if not reasons:
        return None
    text = "\n".join(line for _, body in segments for line in body)
    return text, reasons
