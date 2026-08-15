#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Assert the repository conventions in AGENTS.md, repairing what is mechanical.

    uv run --script .github/scripts/repo_gate.py check
    uv run --script .github/scripts/repo_gate.py fix

A rule reports `Finding` values, and a finding carries its own repair or
`None`. That single field is the whole check/fix distinction: `fix` applies
every repair it is handed, and both modes fail only when a finding arrives
without one, because that is precisely the case a human must judge. Adding a
rule therefore never touches the driver.

`snapshot` performs every read, so each rule is a pure function of an
immutable value and no file is read twice. Repairs are total functions of the
tree, so applying them changes nothing the second time: `fix` is idempotent,
and a run whose repairs were already committed reports clean.

Cost: one pass over the text files, O(bytes) time and space, plus O(k log k)
to order k skill entries. At this repository's scale (order 100 files, a few
megabytes) the whole audit is bounded by reading the tree once.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

# --- Conventions ---

# Escape required because this file is scanned for the forbidden character.
EM_DASH = "\u2014"
TEXT_SUFFIXES = frozenset({".md", ".py", ".toml", ".yml", ".yaml"})
PRUNED_DIRS = frozenset({".git", "__pycache__", ".ruff_cache"})
SPEC_FIELDS = (
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
)
DESCRIPTION_LIMIT = 1024
SKILL_SHEBANG = "#!/usr/bin/env -S uv run --script"
PEP_723_OPEN = "# /// script"
ALIAS_DIR = Path(".github/skills")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Bound repairs in case future rules unlock one another.
FIXPOINT_ROUNDS = 4

# --- Repairs ---


@dataclass(frozen=True, slots=True)
class WriteText:
    path: Path
    text: str

    def apply(self, root: Path) -> None:
        (root / self.path).write_text(self.text)


@dataclass(frozen=True, slots=True)
class MakeSymlink:
    path: Path
    target: str

    def apply(self, root: Path) -> None:
        link = root / self.path
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(self.target)


Repair = WriteText | MakeSymlink


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    path: str
    message: str
    repair: Repair | None = None

    def render(self) -> str:
        mark = "fixable " if self.repair is not None else "blocking"
        return f"{mark} {self.rule:<14} {self.path}: {self.message}"


# --- Snapshot ---


@dataclass(frozen=True, slots=True)
class Repo:
    """An immutable reading of the repository. Every rule below is a pure
    function of this value."""

    skills: frozenset[str]
    texts: Mapping[Path, str]  # repo-relative path to contents
    entry_points: frozenset[Path]  # bundled scripts invoked directly
    aliases: Mapping[str, str | None]  # skill to discovery symlink target


def snapshot(root: Path) -> Repo:
    """Parse a directory into the repository this program knows how to judge.

    Every top-level directory not starting with a dot is a skill directory,
    which AGENTS.md declares a reserved namespace, so the skill set is read
    from the tree rather than from any list that could disagree with it.
    """
    if not (root / "AGENTS.md").is_file():
        raise SystemExit(f"not a skills repository: {root}/AGENTS.md is missing")
    skills = frozenset(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )
    texts: dict[Path, str] = {}
    packages: set[Path] = set()
    for parent, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [name for name in dirnames if name not in PRUNED_DIRS]
        here = Path(parent)
        for name in filenames:
            path = here / name
            if path.is_symlink() or path.suffix not in TEXT_SUFFIXES:
                continue
            relative = path.relative_to(root)
            texts[relative] = path.read_text(encoding="utf-8", errors="replace")
            if name == "__init__.py":
                packages.add(relative.parent)
    aliases = {
        skill: (
            os.readlink(root / ALIAS_DIR / skill)
            if (root / ALIAS_DIR / skill).is_symlink()
            else None
        )
        for skill in skills
    }
    return Repo(skills, texts, _entry_points(texts, skills, packages), aliases)


def _entry_points(
    texts: Mapping[Path, str], skills: frozenset[str], packages: set[Path]
) -> frozenset[Path]:
    """The scripts a skill invokes, which is what the header convention governs.

    A module inside a package directory is imported by an entry point rather
    than run, so it takes neither a shebang nor its own dependency block. That
    distinction is read from where `__init__.py` sits, not from a list here.
    """

    def is_entry_point(path: Path) -> bool:
        # Match path shape directly; short paths fall through.
        match path.parts:
            case (skill, "scripts", *_) if skill in skills:
                return path.suffix == ".py" and path.parent not in packages
            case _:
                return False

    return frozenset(filter(is_entry_point, texts))


# --- Listings ---


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
            (_first_group(r"\[([^\]]+)\]", lines[row]), (lines[row],))
            for row in range(start, end)
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
            name = _first_group(r"`([^`]+)`", line).rstrip("/")
            entries.append((name, [line]))
        elif entries and line.startswith("  ") and line.strip():
            entries[-1][1].append(line)
        else:
            break
        row += 1
    frozen = tuple((name, tuple(body)) for name, body in entries)
    return Listing(tuple(lines[:start]), frozen, tuple(lines[row:]))


def _first_group(pattern: str, line: str) -> str:
    match = re.search(pattern, line)
    return match.group(1) if match else line


# Pair each document with its extractor; do not infer one from another.
LISTINGS: tuple[tuple[Path, Callable[[str], Listing | None]], ...] = (
    (Path("README.md"), _readme_listing),
    (Path("AGENTS.md"), _agents_listing),
)

# --- Rules ---


def rule_em_dash(repo: Repo) -> Iterator[Finding]:
    """AGENTS.md forbids U+2014 outright. The replacement is a hyphen, a comma,
    a colon, or a restructured sentence, which is a judgment, so no repair."""
    for path, text in repo.texts.items():
        if EM_DASH not in text:  # Skip per-line scan for most files.
            continue
        for number, line in enumerate(text.split("\n"), start=1):
            if EM_DASH in line:
                yield Finding(
                    "em-dash",
                    f"{path}:{number}",
                    "em-dash (U+2014); use a hyphen, comma, colon, or rewrite",
                )


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
    for skill in sorted(repo.skills):
        document = Path(skill, "SKILL.md")
        text = repo.texts.get(document)
        if text is None:
            continue  # rule_skill_layout owns the missing-file case
        where = str(document)
        header = FRONTMATTER.match(text)
        if header is None:
            yield Finding("frontmatter", where, "no YAML frontmatter")
            continue
        try:
            fields = yaml.safe_load(header.group(1)) or {}
        except yaml.YAMLError as error:
            yield Finding("frontmatter", where, f"unparseable frontmatter: {error}")
            continue
        yield from _frontmatter_findings(skill, where, fields)


def _frontmatter_findings(skill: str, where: str, fields: dict) -> Iterator[Finding]:
    present = list(fields)
    unknown = [name for name in present if name not in SPEC_FIELDS]
    if unknown:
        yield Finding(
            "frontmatter",
            where,
            f"non-spec fields {unknown}; record such hints under metadata",
        )
    ranked = [SPEC_FIELDS.index(name) for name in present if name in SPEC_FIELDS]
    if ranked != sorted(ranked):
        yield Finding(
            "frontmatter",
            where,
            f"fields out of canonical order: {present} against {list(SPEC_FIELDS)}",
        )
    if fields.get("name") != skill:
        yield Finding(
            "frontmatter", where, f"name {fields.get('name')!r} is not {skill!r}"
        )
    if fields.get("license") != "MIT":
        yield Finding("frontmatter", where, "license must be MIT")
    description = fields.get("description") or ""
    if not description:
        yield Finding("frontmatter", where, "description is required")
    elif len(description) > DESCRIPTION_LIMIT:
        yield Finding(
            "frontmatter",
            where,
            f"description is {len(description)} characters, over {DESCRIPTION_LIMIT}",
        )


def rule_script_header(repo: Repo) -> Iterator[Finding]:
    for path in sorted(repo.entry_points):
        text = repo.texts[path]
        if not text.startswith(SKILL_SHEBANG):
            yield Finding(
                "script-header", str(path), f"must start with {SKILL_SHEBANG}"
            )
        if PEP_723_OPEN not in text:
            yield Finding(
                "script-header", str(path), "needs a PEP 723 `# /// script` block"
            )


def rule_alias(repo: Repo) -> Iterator[Finding]:
    """The discovery alias is a pure function of the skill name, so a missing or
    wrong one is repaired rather than reported."""
    for skill in sorted(repo.skills):
        target = f"../../{skill}"
        if repo.aliases.get(skill) == target:
            continue
        yield Finding(
            "alias",
            str(ALIAS_DIR / skill),
            f"discovery alias must be a symlink to {target}",
            MakeSymlink(ALIAS_DIR / skill, target),
        )


def rule_listings(repo: Repo) -> Iterator[Finding]:
    """Every skill appears in each listing, in order. Ordering is a total
    function of the entries, so it is repaired; a missing entry needs a written
    summary, so it is not."""
    for path, extract in LISTINGS:
        text = repo.texts.get(path)
        if text is None:
            yield Finding("listing", str(path), "document is missing")
            continue
        listing = extract(text)
        if listing is None:
            yield Finding("listing", str(path), "no skill listing found")
            continue
        named = listing.named
        for missing in sorted(repo.skills - set(named)):
            yield Finding("listing", str(path), f"no entry for skill {missing!r}")
        for unknown in sorted(set(named) - repo.skills):
            yield Finding("listing", str(path), f"entry {unknown!r} names no skill")
        if named != sorted(named):
            yield Finding(
                "listing",
                str(path),
                "skill entries are not in alphabetical order",
                WriteText(path, listing.sorted_text()),
            )


RULES: tuple[Callable[[Repo], Iterator[Finding]], ...] = (
    rule_alias,
    rule_em_dash,
    rule_frontmatter,
    rule_listings,
    rule_script_header,
    rule_skill_layout,
)


def audit(repo: Repo) -> list[Finding]:
    return [finding for rule in RULES for finding in rule(repo)]


# --- Shell ---


def repair_to_fixpoint(root: Path) -> tuple[list[Finding], list[Finding]]:
    """Apply repairs until none remain, re-auditing between rounds so the
    verdict describes the tree as it now stands rather than as it was."""
    applied: list[Finding] = []
    findings = audit(snapshot(root))
    for _ in range(FIXPOINT_ROUNDS):
        pending = [(f, f.repair) for f in findings if f.repair is not None]
        if not pending:
            break
        for finding, repair in pending:
            repair.apply(root)
            applied.append(finding)
        findings = audit(snapshot(root))
    return applied, findings


def report(applied: Sequence[Finding], findings: Sequence[Finding]) -> int:
    """Print what was repaired and what remains, then fail if anything remains.

    The two remaining classes are reported separately because they ask for
    different actions: a mechanical finding asks for `fix`, and only a finding
    without a repair asks for a person. After `fix` the first class is empty
    unless a repair failed to settle, which is why it is still worth naming.
    """
    for finding in applied:
        print(f"repaired {finding.rule:<14} {finding.path}", file=sys.stderr)
    for finding in sorted(findings, key=lambda f: (f.repair is None, f.rule, f.path)):
        print(finding.render(), file=sys.stderr)
    mechanical = sum(f.repair is not None for f in findings)
    blocking = len(findings) - mechanical
    if mechanical:
        print(
            f"\n{mechanical} finding(s) are mechanical; run repo_gate.py fix.",
            file=sys.stderr,
        )
    if blocking:
        print(f"\n{blocking} finding(s) need a human.", file=sys.stderr)
    if findings:
        return 1
    print("repository conventions hold.", file=sys.stderr)
    return 0


def main(argv: Sequence[str]) -> int:
    mode = argv[0] if argv else "check"
    root = Path(__file__).resolve().parents[2]
    match mode:
        case "check":
            return report((), audit(snapshot(root)))
        case "fix":
            return report(*repair_to_fixpoint(root))
        case _:
            print("usage: repo_gate.py [check | fix]", file=sys.stderr)
            return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
