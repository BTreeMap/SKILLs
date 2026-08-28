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

`snapshot` performs every read and every parse, so each rule is a total
function of an immutable value and no file is read twice. Filesystem and
manifest states arrive as closed sums (`LinkState`, `ManifestState`) rather
than booleans or sentinels, and a repair is constructed only against a state
it can settle, so a repair that would fail is unrepresentable. Repairs are
total functions of the tree, so applying them changes nothing the second
time: `fix` is idempotent, and a run whose repairs were already committed
reports clean. The driver applies at most one repair per path per round;
anything deferred by that guard re-derives from the fresh snapshot of the
next round, so two findings can never overwrite each other's work.

Cost: one pass over the text files, O(bytes) time and space, plus O(k log k)
to order k skill entries. At this repository's scale (order 100 files, a few
megabytes) the whole audit is bounded by reading the tree once.
"""

from __future__ import annotations

import json
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
# Tool-managed trees hold third-party text this repository's conventions do not
# govern, so the walk stops at each one rather than judging its contents.
PRUNED_DIRS = frozenset(
    {".git", "__pycache__", ".ruff_cache", ".venv", ".pytest_cache", ".mypy_cache"}
)
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
# The one abbreviation this repository publishes under: the marketplace name,
# the plugin name, and (by convention documented in AGENTS.md) the XDG state
# root that bundled scripts write beneath.
BRAND = "btm-skills"
# `skills/` is the vendor-neutral hub: one relative symlink per skill, pointing
# back at the canonical root directory. Each vendor path is a single symlink to
# that hub, so supporting another agent costs one link rather than one per
# skill. Installers resolve skills through the manifests instead, which declare
# the canonical paths.
HUB = Path("skills")
VENDOR_LINKS = (Path(".claude/skills"), Path(".github/skills"))
# The shared kernel package consumer scripts declare as a uv path dependency
# (`../.corekit`, resolved lexically). Each consumer skill carries a dotted
# `.corekit` symlink to the repository kernel, so the dependency lands on the
# same package through the canonical path, the hub, and every vendor path.
KERNEL = Path(".corekit")
MARKETPLACE = Path(".claude-plugin/marketplace.json")
PLUGIN_MANIFEST = Path(".claude-plugin/plugin.json")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Bound repairs in case future rules unlock one another.
FIXPOINT_ROUNDS = 4


def _relative_target(link: Path, dest: Path) -> str:
    """The symlink target from `link` to `dest`, both repo-relative.

    Pure path arithmetic, so an alias target can never disagree with the
    location it is derived from, and a link always names a destination
    distinct from itself.
    """
    assert link != dest, f"self-link: {link}"
    return os.path.relpath(dest, link.parent)


# --- Repairs ---


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


# --- Snapshot ---


@dataclass(frozen=True, slots=True)
class Symlink:
    target: str


@dataclass(frozen=True, slots=True)
class Absent:
    pass


@dataclass(frozen=True, slots=True)
class LinkFarm:
    """A real directory whose children are all symlinks: rebuildable by
    derivation, so mechanically removable."""


@dataclass(frozen=True, slots=True)
class Occupied:
    """A regular file, or a directory holding real content: work this program
    cannot rebuild, so never mechanically removable."""


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
    doc: dict  # shallowly immutable; rules copy before rewriting


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
    """An immutable reading of the repository. Every rule below is a pure
    function of this value."""

    skills: frozenset[str]
    texts: Mapping[Path, str]  # repo-relative path to contents
    entry_points: frozenset[Path]  # bundled scripts invoked directly
    links: Mapping[Path, LinkState]  # hub, its entries, and the vendor paths
    manifests: Mapping[Path, ManifestState]


def snapshot(root: Path) -> Repo:
    """Parse a directory into the repository this program knows how to judge.

    Every top-level directory that is neither dotted nor the `skills/` hub is
    a skill directory, which AGENTS.md declares a reserved namespace, so the
    skill set is read from the tree rather than from any list that could
    disagree with it.
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
    links: dict[Path, LinkState] = {HUB: _link_state(root / HUB)}
    for vendor in VENDOR_LINKS:
        links[vendor] = _link_state(root / vendor)
    for skill in skills:
        kernel_link = Path(skill) / KERNEL.name
        links[kernel_link] = _link_state(root / kernel_link)
    # Hub entries exist only inside a real hub directory; through a symlinked
    # hub they would describe some other tree, so they are not read.
    if isinstance(links[HUB], LinkFarm | Occupied):
        present = {entry.name for entry in (root / HUB).iterdir()}
    else:
        present = set()
    for name in skills | present:
        links[HUB / name] = _link_state(root / HUB / name)
    manifests = {
        path: _manifest_state(root / path) for path in (MARKETPLACE, PLUGIN_MANIFEST)
    }
    return Repo(skills, texts, _entry_points(texts, skills, packages), links, manifests)


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
        header = FRONTMATTER.match(text)
        if header is None:
            yield Finding("frontmatter", where, "no YAML frontmatter")
            continue
        try:
            fields = yaml.safe_load(header.group(1)) or {}
        except yaml.YAMLError as error:
            yield Finding("frontmatter", where, f"unparseable frontmatter: {error}")
            continue
        if not isinstance(fields, dict):
            yield Finding("frontmatter", where, "frontmatter is not a mapping")
            continue
        yield from _frontmatter_judgments(where, fields)
        normalized = _canonical_header(skill, fields, header.group(1))
        if normalized is not None:
            new_header, reasons = normalized
            repaired = f"---\n{new_header}\n---\n{text[header.end() :]}"
            yield Finding(
                "frontmatter",
                where,
                "; ".join(reasons),
                WriteText(document, repaired),
            )


def _frontmatter_judgments(where: str, fields: dict) -> Iterator[Finding]:
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
    skill: str, fields: dict, header: str
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


def rule_alias(repo: Repo) -> Iterator[Finding]:
    """Every alias is a pure function of the skill set, so a missing, wrong,
    orphaned, or legacy-shaped one is repaired. Only real content blocks,
    because deleting it would destroy work no derivation can rebuild.

    Two standards bound the derivation: the hub aliases exactly the visible
    top-level directories (the reserved skill namespace; dotted
    infrastructure is wired by rule_kernel), and every alias targets a
    destination distinct from itself (_relative_target asserts it)."""
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
    # This rule owns the hub and the vendor paths; per-skill kernel links
    # belong to rule_kernel.
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


def rule_manifest(repo: Repo) -> Iterator[Finding]:
    """The manifests publish this repository under one brand and declare every
    skill path, which is what makes discovery declared rather than a fallback
    scan. Names and the skill list are functions of `BRAND` and the tree, so
    drift is repaired; absent or unreadable content needs a person."""
    for path in sorted(repo.manifests):
        match repo.manifests[path]:
            case Absent():
                yield Finding("manifest", str(path), "manifest is missing")
            case Unreadable(reason):
                yield Finding("manifest", str(path), f"unreadable manifest: {reason}")
            case Parsed(doc):
                yield from _manifest_findings(path, doc, repo.skills)


def _manifest_findings(
    path: Path, doc: dict, skills: frozenset[str]
) -> Iterator[Finding]:
    canonical = json.loads(json.dumps(doc))  # independent copy; `doc` stays pure
    reasons: list[str] = []
    if canonical.get("name") != BRAND:
        canonical["name"] = BRAND
        reasons.append(f"name set to {BRAND!r}")
    if path == MARKETPLACE:
        plugins = canonical.get("plugins")
        if not (isinstance(plugins, list) and plugins and isinstance(plugins[0], dict)):
            yield Finding(
                "manifest", str(path), "plugins[0] is not an object; restructure it"
            )
            return
        entry = plugins[0]
        if entry.get("name") != BRAND:
            entry["name"] = BRAND
            reasons.append(f"plugin name set to {BRAND!r}")
        declared = [f"./{skill}" for skill in sorted(skills)]
        if entry.get("skills") != declared:
            entry["skills"] = declared
            reasons.append("skill list regenerated from the tree")
    if reasons:
        yield Finding(
            "manifest",
            str(path),
            "; ".join(reasons),
            WriteText(path, json.dumps(canonical, indent=2) + "\n"),
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
    rule_kernel,
    rule_listings,
    rule_manifest,
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
        # One writer per path per round: a repair deferred here re-derives
        # from the next round's fresh snapshot, so no update is ever lost.
        claimed: set[Path] = set()
        for finding, repair in pending:
            if repair.path in claimed:
                continue
            claimed.add(repair.path)
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
