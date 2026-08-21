#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Deterministic guard for the caveman compress mode.

The agent performs the actual prose compression; this script does everything
an LLM is bad at, deterministically:

  check <file>              report hard admissibility plus advisory signals
  prepare <file>            admit the file, write a verified out-of-tree
                            backup, emit the compressible body to a work file
  apply <file> <body-file>  validate the compressed body against the backup;
                            atomic-write the target only when validation passes
  restore <file>            undo a completed compression from its backup
  clean <file> | --all      delete one file's backup artifacts, or the whole
                            backup tree (destroys the undo)
  self-test                 run the built-in invariant checks

The target file is never written until validation passes, so it never holds a
half-valid state. Output is plain ASCII. Stdlib only; run with
`uv run --script` per the PEP 723 metadata above.

Division of labor (neuro-symbolic): this script is the symbolic half. It owns
what is exact (backup identity, atomic writes, structural equality) and
refuses (exit 1) only on invariant violations: missing/oversized/non-UTF-8/
empty files, secret-like names, backup artifacts. Content-type judgment is
heuristic, so it is never a verdict here: it is emitted as SIGNAL lines for
the compressing agent, the neuro half, to weigh. A signal never blocks;
the verified backup keeps every judgment call undoable.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from pathlib import Path
from typing import ClassVar

MAX_FILE_SIZE = 500_000  # bytes; split larger prose files first

# --- Pure domain model ---


class FileKind(Enum):
    NATURAL_LANGUAGE = "natural_language"
    CODE = "code"
    CONFIG = "config"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Refusal:
    """Invariant violation: the only thing the symbolic side may block on."""

    reason: str


@dataclass(frozen=True, slots=True)
class Assessment:
    """Heuristic reading of a file: a best-guess kind plus the evidence that
    produced it. Advisory by construction: the compressing agent owns the
    judgment; only `Refusal` (exact invariants) blocks."""

    kind: FileKind
    signals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Plan:
    """An admitted compression: the single trusted entry into the domain.

    `split_frontmatter` partitions the source text, so the invariant
    `original == frontmatter + body` holds by construction; nothing ever
    needs to re-read the source to recover the original. `notes` carries
    the advisory signals for the agent; it never gates.
    """

    path: Path
    frontmatter: str
    body: str
    notes: tuple[str, ...] = ()

    @property
    def original(self) -> str:
        return self.frontmatter + self.body


Admission = Plan | Refusal


@dataclass(frozen=True, slots=True)
class Verdict:
    """Validation outcome. A monoid: EMPTY is the identity, `merge` is
    associative, and `validate` is a fold of independent checks under it."""

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    EMPTY: ClassVar[Verdict]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def merge(self, other: Verdict) -> Verdict:
        return Verdict(self.errors + other.errors, self.warnings + other.warnings)

    @staticmethod
    def error(msg: str) -> Verdict:
        return Verdict(errors=(msg,))

    @staticmethod
    def warning(msg: str) -> Verdict:
        return Verdict(warnings=(msg,))


Verdict.EMPTY = Verdict()


# --- Classification ---

COMPRESSIBLE_EXTENSIONS = frozenset(
    {".md", ".txt", ".markdown", ".rst", ".typ", ".typst", ".tex"}
)
# Compressible, but the structural checks assume Markdown syntax: reST titles
# are underlined, LaTeX sections are \section{...} commands, Typst headings
# are '='-runs: none visible to the Markdown extractors, so validation is
# vacuous there and the agent must be told rather than silently unprotected.
NON_MARKDOWN_PROSE_EXTENSIONS = frozenset({".rst", ".tex", ".typ", ".typst"})
CONFIG_EXTENSIONS = frozenset(
    {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".env",
        ".properties",
        ".plist",
        # Tabular data (RFC 4180: spreadsheet interchange), not code.
        ".csv",
        ".tsv",
        # Infrastructure/data description languages.
        ".tf",
        ".tfvars",
        ".hcl",
    }
)
# fmt: off
CODE_EXTENSIONS = frozenset(
    {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
        ".css", ".scss", ".html", ".xml", ".sql",
        ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".bat", ".cmd",
        ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
        ".rb", ".php", ".swift", ".kt", ".kts", ".lua",
        ".cs", ".fs", ".fsx", ".vb", ".scala", ".sc", ".groovy", ".gradle",
        ".hs", ".lhs", ".ml", ".mli", ".ex", ".exs", ".erl", ".hrl",
        ".clj", ".cljs", ".lisp", ".el", ".scm", ".rkt",
        ".r", ".jl", ".dart", ".zig", ".nim", ".cr", ".pl", ".pm",
        ".m", ".mm", ".d", ".pas", ".f90", ".asm", ".s",
        ".vue", ".svelte", ".astro", ".proto", ".graphql", ".sol",
        ".nix", ".tcl", ".vim", ".ipynb",
        ".lock", ".dockerfile", ".makefile",
    }
)
# fmt: on
KNOWN_CODE_FILENAMES = frozenset(
    {
        "dockerfile",
        "makefile",
        "gnumakefile",
        "jenkinsfile",
        "vagrantfile",
        "rakefile",
        "gemfile",
        "justfile",
        "procfile",
        "brewfile",
        "cmakelists.txt",
    }
)
CODE_LINE_PATTERNS = tuple(
    re.compile(p)
    for p in (
        r"^\s*(import |from .+ import |require\(|const |let |var )",
        r"^\s*(def |class |function |async function |export )",
        r"^\s*(func |fn |package |module |namespace |struct |impl |trait |pub )",
        r"^\s*(#include|#define|#pragma|#import)\b",
        r"^\s*(SELECT|INSERT INTO|UPDATE|DELETE FROM|CREATE|ALTER|FROM|WHERE|JOIN)\b",
        r"^\s*\w[\w']*\s*::",  # Haskell type signatures, C++ scope resolution
        r"^\s*(if\s*\(|for\s*\(|while\s*\(|switch\s*\(|try\s*\{)",
        r"^\s*[\}\]\);]+\s*$",
        r".*[;{}]\s*$",  # statement/brace line endings
        r"^\s*@\w+",
        r'^\s*"[^"]+"\s*:\s*',
        r"^\s*\w+\s*=\s*[{\[\(\"']",
    )
)
# A line counts as prose evidence only positively: a Markdown marker with a
# word after it, or two-plus words free of code punctuation. Extensionless
# files showing neither enough code nor enough prose stay UNKNOWN (signaled).
PROSE_MARKER_REGEX = re.compile(r"^ {0,3}(?:#{1,6}|[-*+>]|\d{1,9}[.)])[ \t]+")
PROSE_CODE_CHARS_REGEX = re.compile(r"[{};=`$<>\\]|\(\)|::|->")
PROSE_WORD_REGEX = re.compile(r"[A-Za-z]{2,}")


def _is_code_line(line: str) -> bool:
    return any(p.match(line) for p in CODE_LINE_PATTERNS)


def _is_prose_line(line: str) -> bool:
    if _is_code_line(line):
        return False
    has_marker = bool(PROSE_MARKER_REGEX.match(line))
    stripped = PROSE_MARKER_REGEX.sub("", line)
    if PROSE_CODE_CHARS_REGEX.search(stripped):
        return False
    return len(PROSE_WORD_REGEX.findall(stripped)) >= (1 if has_marker else 2)


def _looks_like_json(text: str) -> bool:
    # RFC 8259 admits bare scalars as JSON texts ("42" parses); only a
    # top-level object or array is evidence of a config file.
    try:
        return isinstance(json.loads(text), dict | list)
    except ValueError:
        return False


def _looks_like_yaml(lines: list[str]) -> bool:
    def is_indicator(stripped: str) -> bool:
        return bool(
            stripped.startswith("---")
            or re.match(r"^\w[\w\s]*:\s", stripped)
            or (stripped.startswith("- ") and ":" in stripped)
        )

    stripped_head = [s for line in lines[:30] if (s := line.strip())]
    return bool(stripped_head) and (
        # More than 60% of nonblank header lines must look like YAML.
        sum(map(is_indicator, stripped_head)) / len(stripped_head) > 0.6  # noqa: PLR2004
    )


def assess(path: Path, text: str | None) -> Assessment:  # noqa: PLR0911
    """Assess by basename, then extension, then content (extensionless).

    Every heuristic observation becomes a signal with its evidence stated
    (ratios, matched taxonomy), so the agent can weigh it; nothing here is
    a verdict. Precedence stays one-return-per-rule for visibility.
    """
    name = path.name.lower()
    if name in KNOWN_CODE_FILENAMES:
        return Assessment(
            FileKind.CODE, (f"'{path.name}' is a known build/tool filename",)
        )
    if name.startswith(".env"):
        # Dotfiles have no pathlib suffix: Path(".env").suffix == "".
        return Assessment(
            FileKind.CONFIG, (f"'{path.name}' is an environment/config file",)
        )
    ext = path.suffix.lower()
    if ext in COMPRESSIBLE_EXTENSIONS:
        return Assessment(FileKind.NATURAL_LANGUAGE)
    if ext in CONFIG_EXTENSIONS:
        return Assessment(
            FileKind.CONFIG, (f"extension '{ext}' is a config/data format",)
        )
    if ext in CODE_EXTENSIONS:
        return Assessment(FileKind.CODE, (f"extension '{ext}' is a code format",))
    if ext or text is None:
        return Assessment(
            FileKind.UNKNOWN,
            (f"extension '{ext or '(none)'}' is not in any known taxonomy",),
        )
    if text.startswith("#!"):
        return Assessment(
            FileKind.CODE, ("first line is a '#!' shebang: an executable script",)
        )
    if _looks_like_json(text[:10_000]):
        return Assessment(
            FileKind.CONFIG, ("content parses as a JSON object or array",)
        )
    head = [s for line in text.splitlines()[:50] if (s := line.strip())]
    if not head:
        return Assessment(FileKind.UNKNOWN, ("no content to assess",))
    code_pct = round(100 * sum(map(_is_code_line, head)) / len(head))
    prose_pct = round(100 * sum(map(_is_prose_line, head)) / len(head))
    evidence = (
        f"content evidence (first {len(head)} nonblank lines):"
        f" {code_pct}% code-like, {prose_pct}% prose-like"
    )
    if _looks_like_yaml(text.splitlines()[:30]):
        return Assessment(
            FileKind.CONFIG,
            (
                evidence,
                "head lines look like YAML mappings ('Word: text' prose can"
                " also match, so judge yourself)",
            ),
        )
    if code_pct > 40:  # noqa: PLR2004
        return Assessment(FileKind.CODE, (evidence,))
    if prose_pct > 50:  # noqa: PLR2004
        return Assessment(FileKind.NATURAL_LANGUAGE, (evidence,))
    return Assessment(
        FileKind.UNKNOWN,
        (evidence, "neither strong code nor strong prose evidence"),
    )


def classify(path: Path, text: str | None) -> FileKind:
    """Projection of `assess` for callers that only need the kind."""
    return assess(path, text).kind


# --- Sensitivity refusal ---

SENSITIVE_BASENAME_REGEX = re.compile(
    r"(?ix)^("
    r"\.env(\..+)?|\.netrc|credentials(\..+)?|secrets?(\..+)?"
    r"|passwords?(\..+)?|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?"
    r"|authorized_keys|known_hosts"
    r"|.*\.(pem|key|p12|pfx|crt|cer|jks|keystore|asc|gpg)"
    r")$"
)
SENSITIVE_PATH_COMPONENTS = frozenset({".ssh", ".aws", ".gnupg", ".kube", ".docker"})
SENSITIVE_NAME_TOKENS = (
    "secret",
    "credential",
    "password",
    "passwd",
    "apikey",
    "accesskey",
    "token",
    "privatekey",
)


def is_sensitive(path: Path) -> bool:
    """Files that must never enter a compression flow, by name alone."""
    if SENSITIVE_BASENAME_REGEX.match(path.name):
        return True
    if {p.lower() for p in path.parts} & SENSITIVE_PATH_COMPONENTS:
        return True
    collapsed = re.sub(r"[_\-\s.]", "", path.name.lower())
    return any(token in collapsed for token in SENSITIVE_NAME_TOKENS)


# --- Markdown structure ---

FRONTMATTER_REGEX = re.compile(r"\A(---\r?\n.*?\r?\n---\r?\n)(.*)", re.DOTALL)
FENCE_OPEN_REGEX = re.compile(r"^(\s{0,3})(`{3,}|~{3,})(.*)$")
# CommonMark ATX: 0-3 spaces of indent, 1-6 '#', then space/tab (never a
# newline) or end of line; empty headings are legal.
ATX_HEADING_REGEX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
# CommonMark setext underline: a run of '=' (level 1) or '-' (level 2)
# directly under a paragraph line.
SETEXT_UNDERLINE_REGEX = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
INDENTED_LINE_REGEX = re.compile(r"^(?: {4,}|\t)")
LIST_ITEM_REGEX = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])[ \t]")
BULLET_REGEX = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
URL_REGEX = re.compile(r"https?://[^\s)]+")
PATH_REGEX = re.compile(
    r"(?:\./|\.\./|/|[A-Za-z]:\\)[\w\-/\\.]+|[\w\-.]+[/\\][\w\-/\\.]+"
)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Partition text into (frontmatter, body); concatenation restores it."""
    m = FRONTMATTER_REGEX.match(text)
    return (m.group(1), m.group(2)) if m else ("", text)


def partition_fences(text: str) -> tuple[tuple[str, ...], str]:
    """One pass over the lines: (fenced blocks in order, remaining prose).

    CommonMark rules: a closing fence uses the same character, is at least as
    long as the opener, and carries no info string. Unclosed fences are
    treated as prose so malformed markdown cannot hide a validation failure.
    A fence scan is a state machine; a loop is its honest shape.
    """
    blocks: list[str] = []
    prose: list[str] = []
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        m = FENCE_OPEN_REGEX.match(lines[i])
        if not m:
            prose.append(lines[i])
            i += 1
            continue
        fence_char, fence_len = m.group(2)[0], len(m.group(2))
        start = i
        i += 1
        while i < n:
            close = FENCE_OPEN_REGEX.match(lines[i])
            if (
                close
                and close.group(2)[0] == fence_char
                and len(close.group(2)) >= fence_len
                and close.group(3).strip() == ""
            ):
                blocks.append("\n".join(lines[start : i + 1]))
                i += 1
                break
            i += 1
        else:
            prose.extend(lines[start:])
    return tuple(blocks), "\n".join(prose)


def partition_indented(text: str) -> tuple[tuple[str, ...], str]:
    """Indented (4-space/tab) code blocks from fence-free text.

    CommonMark approximation: a run of 4+-indented non-blank lines counts as
    code only when preceded by a blank line (indented code cannot interrupt a
    paragraph) and the nearest preceding non-blank line is not a list item
    (there, 4-space indentation is usually list continuation, not code).
    Blank-separated runs compare as separate blocks; that is symmetric across
    the two texts being validated, which is all equality checking needs.
    """
    blocks: list[str] = []
    prose: list[str] = []
    lines = text.split("\n")
    i, n = 0, len(lines)
    prev_blank = True
    last_nonblank = ""
    while i < n:
        line = lines[i]
        if (
            prev_blank
            and line.strip()
            and INDENTED_LINE_REGEX.match(line)
            and not LIST_ITEM_REGEX.match(last_nonblank)
        ):
            start = i
            while i < n and lines[i].strip() and INDENTED_LINE_REGEX.match(lines[i]):
                i += 1
            blocks.append("\n".join(lines[start:i]))
            prev_blank, last_nonblank = False, lines[i - 1]
            continue
        prose.append(line)
        prev_blank = not line.strip()
        if line.strip():
            last_nonblank = line
        i += 1
    return tuple(blocks), "\n".join(prose)


def markdown_prose(text: str) -> str:
    """Text with fenced and indented code blocks removed."""
    _, rest = partition_fences(text)
    return partition_indented(rest)[1]


def extract_headings(text: str) -> tuple[tuple[str, str], ...]:
    """ATX and setext headings in document order, from fence-free text only,
    so '#' comments inside fenced code are never mistaken for headings.
    Setext levels are recorded as '=' (h1) and '-' (h2)."""
    _, prose = partition_fences(text)
    headings: list[tuple[str, str]] = []
    prev: str | None = None  # candidate paragraph line above a setext underline
    for line in prose.split("\n"):
        if m := ATX_HEADING_REGEX.match(line):
            headings.append((m.group(1), (m.group(2) or "").strip()))
            prev = None
            continue
        if prev is not None and SETEXT_UNDERLINE_REGEX.match(line):
            headings.append(("=" if "=" in line else "-", prev.strip()))
            prev = None
            continue
        prev = line if line.strip() else None
    return tuple(headings)


def _trim_trailing_punctuation(match: str) -> str:
    """Sentence punctuation after a URL or path is prose, not address."""
    return match.rstrip(".,;:!?")


def extract_urls(text: str) -> frozenset[str]:
    return frozenset(map(_trim_trailing_punctuation, URL_REGEX.findall(text)))


def extract_paths(text: str) -> frozenset[str]:
    return frozenset(map(_trim_trailing_punctuation, PATH_REGEX.findall(text)))


def extract_inline_codes(text: str) -> Counter[str]:
    return Counter(re.findall(r"`([^`]+)`", markdown_prose(text)))


# --- Validation ---


def _check_headings(original: str, compressed: str) -> Verdict:
    orig, comp = extract_headings(original), extract_headings(compressed)
    if orig != comp:
        return Verdict.error(
            f"Headings not preserved exactly: {len(orig)} vs {len(comp)}"
        )
    return Verdict.EMPTY


def _check_code_blocks(original: str, compressed: str) -> Verdict:
    orig_fences, orig_rest = partition_fences(original)
    comp_fences, comp_rest = partition_fences(compressed)
    verdict = Verdict.EMPTY
    if orig_fences != comp_fences:
        verdict = verdict.merge(
            Verdict.error("Fenced code blocks not preserved exactly (content, order)")
        )
    if partition_indented(orig_rest)[0] != partition_indented(comp_rest)[0]:
        verdict = verdict.merge(
            Verdict.error("Indented code blocks not preserved exactly (content, order)")
        )
    return verdict


def _check_urls(original: str, compressed: str) -> Verdict:
    orig, comp = extract_urls(original), extract_urls(compressed)
    if orig != comp:
        return Verdict.error(
            f"URL mismatch: lost={set(orig - comp)}, added={set(comp - orig)}"
        )
    return Verdict.EMPTY


def _check_inline_codes(original: str, compressed: str) -> Verdict:
    orig, comp = extract_inline_codes(original), extract_inline_codes(compressed)
    lost, added = orig - comp, comp - orig
    verdict = Verdict.EMPTY
    if lost:
        verdict = verdict.merge(Verdict.error(f"Inline code lost: {sorted(lost)}"))
    if added:
        verdict = verdict.merge(Verdict.warning(f"Inline code added: {sorted(added)}"))
    return verdict


def _check_paths(original: str, compressed: str) -> Verdict:
    orig, comp = extract_paths(original), extract_paths(compressed)
    if orig != comp:
        return Verdict.warning(
            f"Path mismatch: lost={set(orig - comp)}, added={set(comp - orig)}"
        )
    return Verdict.EMPTY


def _check_bullets(original: str, compressed: str) -> Verdict:
    orig = len(BULLET_REGEX.findall(original))
    comp = len(BULLET_REGEX.findall(compressed))
    # Allow 15% bullet-count drift.
    if orig and abs(orig - comp) / orig > 0.15:  # noqa: PLR2004
        return Verdict.warning(f"Bullet count drifted: {orig} -> {comp}")
    return Verdict.EMPTY


CHECKS = (
    _check_headings,
    _check_code_blocks,
    _check_urls,
    _check_inline_codes,
    _check_paths,
    _check_bullets,
)


def validate(original: str, compressed: str) -> Verdict:
    """Fold the independent checks under the Verdict monoid."""
    return reduce(
        Verdict.merge, (check(original, compressed) for check in CHECKS), Verdict.EMPTY
    )


# --- Filesystem effects ---


def backup_base() -> Path:
    """Out-of-tree backup root so skill auto-loaders never re-ingest backups.

    Durable state lands in the library's unified namespace under the XDG
    state directory (LOCALAPPDATA on Windows), per repository convention.
    """
    if os.name == "nt":
        base = Path(
            os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        )
    else:
        base = Path(
            os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
        )
    return base / "btm-skills" / "caveman" / "backups"


@dataclass(frozen=True, slots=True)
class BackupSlot:
    """One target's backup directory plus the source path it must belong to."""

    directory: Path
    source: Path

    @property
    def backup_path(self) -> Path:
        return self.directory / "original.md"

    @property
    def body_path(self) -> Path:
        return self.directory / "body.md"

    @property
    def meta_path(self) -> Path:
        return self.directory / "meta.json"


def slot_for(target: Path) -> BackupSlot:
    """Derive the backup slot for a resolved path.

    The rule: slug(name) + "-" + first 16 hex of sha256(fsencode(path)).
    Deterministic (a pure function of the path) and total (os.fsencode hashes
    any representable filename, including non-UTF-8 surrogates). The digest
    makes accidental collision ~n^2/2^65; `load_slot` then proves identity
    against meta.json, so even a collision refuses instead of touching another
    file's backup. The component is ASCII, <= 81 bytes, and separator-free.
    """
    digest = hashlib.sha256(os.fsencode(target)).hexdigest()[:16]
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", target.name)[:64] or "file"
    return BackupSlot(directory=backup_base() / f"{slug}-{digest}", source=target)


def recorded_source(slot: BackupSlot) -> str | None:
    """The source path a slot's meta.json claims, or None if absent/corrupt."""
    raw = read_utf8(slot.meta_path) if slot.meta_path.is_file() else None
    if raw is None:
        return None
    try:
        meta = json.loads(raw)
    except ValueError:
        return None
    source = meta.get("source") if isinstance(meta, dict) else None
    return source if isinstance(source, str) else None


def load_slot(target: Path) -> BackupSlot | Refusal:
    """The one trusted way to reach an existing backup: prove identity first."""
    slot = slot_for(target)
    if not slot.backup_path.is_file():
        return Refusal(f"no backup found at {slot.backup_path}; run prepare first")
    recorded = recorded_source(slot)
    if recorded is None:
        return Refusal(
            f"backup metadata missing or unreadable: {slot.meta_path}; refusing to"
            " touch this slot (clean <file> removes it)"
        )
    if recorded != str(target):
        return Refusal(
            f"backup identity mismatch: {slot.directory} records {recorded};"
            " refusing to touch another file's backup"
        )
    return slot


def read_utf8(path: Path) -> str | None:
    """Strict UTF-8 read; None means undecodable, never silent corruption."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def write_text_atomic(path: Path, text: str) -> None:
    """Encode first, write a sibling temp file, fsync, then os.replace().

    The destination only ever moves from one complete file to another;
    permission bits survive the swap.
    """
    data = text.encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            os.chmod(tmp_path, stat.S_IMODE(path.stat().st_mode))
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


# Guidance the agent receives alongside a non-prose assessment. Advisory:
# the agent weighs it against user intent; the backup keeps either call safe.
KIND_GUIDANCE = {
    FileKind.CODE: (
        "assessed as CODE: compressing source code is almost never intended;"
        " stop and report unless the user explicitly asked for this exact file"
    ),
    FileKind.CONFIG: (
        "assessed as CONFIG/DATA: caveman compression rarely applies;"
        " proceed only on explicit user intent"
    ),
    FileKind.UNKNOWN: (
        "assessment inconclusive: read the file and judge whether it is"
        " prose before compressing"
    ),
}


def admit(path: Path) -> Admission:  # noqa: PLR0911
    """Parse, don't validate: every refusal reason lives here, once.

    Refusals are exact invariants only. Heuristic content judgment becomes
    advisory notes on the Plan; the compressing agent owns that decision.
    """
    # Preserve distinct refusal reasons and exit statuses.
    path = path.resolve()
    if not path.is_file():
        return Refusal(f"Not a file: {path}")
    if is_sensitive(path):
        return Refusal(
            f"Refusing {path.name}: filename looks sensitive (credentials, keys,"
            " secrets, or known private paths). Rename it if this is a false positive."
        )
    if path.name.endswith(".original.md") or backup_base().resolve() in path.parents:
        return Refusal("Refusing to compress a backup file")
    if path.stat().st_size > MAX_FILE_SIZE:
        return Refusal(f"File exceeds {MAX_FILE_SIZE // 1000}KB; split it first")
    text = read_utf8(path)
    if text is None:
        return Refusal("File is not valid UTF-8")
    if not text.strip():
        return Refusal("File is empty or whitespace-only")
    frontmatter, body = split_frontmatter(text)
    if not body.strip():
        return Refusal("Body is empty after frontmatter removal")
    assessment = assess(path, text)
    notes = assessment.signals
    if assessment.kind is not FileKind.NATURAL_LANGUAGE:
        notes = (KIND_GUIDANCE[assessment.kind], *notes)
    return Plan(path=path, frontmatter=frontmatter, body=body, notes=notes)


def print_signals(plan: Plan) -> None:
    """Hand the heuristic evidence to the agent; advisory, never blocking."""
    for note in plan.notes:
        print(f"SIGNAL: {note}")
    if plan.notes:
        print(
            "Signals are advisory: weigh them against the user's actual request"
            " before compressing (restore undoes everything)."
        )


def print_format_warning(path: Path) -> None:
    if path.suffix.lower() in NON_MARKDOWN_PROSE_EXTENSIONS:
        print(
            f"WARNING: structural validation assumes Markdown; {path.suffix}"
            " headings and code blocks are NOT protected by the checks;"
            " preserve structure manually and with extra care"
        )


def cmd_check(path: Path) -> int:
    match admit(path):
        case Refusal(reason):
            print(f"REFUSED: {reason}")
            return 1
        case Plan() as plan:
            fm = "yes" if plan.frontmatter else "no"
            print(f"OK: admissible (frontmatter: {fm}, body: {len(plan.body)} chars)")
            print_signals(plan)
            print_format_warning(plan.path)
            return 0
    raise AssertionError("unreachable: Admission is a closed union")


def cmd_prepare(path: Path) -> int:
    match admit(path):
        case Refusal(reason):
            print(f"REFUSED: {reason}")
            return 1
        case Plan() as plan:
            slot = slot_for(plan.path)
            recorded = recorded_source(slot)
            if recorded is not None and recorded != str(plan.path):
                print(
                    f"REFUSED: backup slot collision: {slot.directory} records"
                    f" {recorded}; refusing to touch another file's backup"
                )
                return 1
            if slot.backup_path.exists():
                print(
                    f"REFUSED: backup already exists: {slot.backup_path}\n"
                    "Remove or restore it first; refusing to overwrite a prior "
                    "original."
                )
                return 1
            slot.directory.mkdir(parents=True, exist_ok=True)
            # Identity before content: a backup must never exist anonymously.
            write_text_atomic(slot.meta_path, json.dumps({"source": str(plan.path)}))
            write_text_atomic(slot.backup_path, plan.original)
            if read_utf8(slot.backup_path) != plan.original:
                slot.backup_path.unlink(missing_ok=True)
                print("REFUSED: backup readback mismatch; aborting before any change")
                return 1
            write_text_atomic(slot.body_path, plan.body)
            print(f"BACKUP: {slot.backup_path}")
            print(f"BODY:   {slot.body_path}")
            print_signals(plan)
            print_format_warning(plan.path)
            print(
                "Compress the BODY file's prose, then run: "
                "apply <file> <compressed-body>"
            )
            return 0
    raise AssertionError("unreachable: Admission is a closed union")


def cmd_apply(path: Path, compressed_body_path: Path) -> int:  # noqa: PLR0911
    # Preserve each refusal's contract and exit status.
    path = path.resolve()
    slot = load_slot(path)
    if isinstance(slot, Refusal):
        print(f"REFUSED: {slot.reason}")
        return 1
    if not compressed_body_path.is_file():
        print(f"REFUSED: compressed body not found: {compressed_body_path}")
        return 1
    original = read_utf8(slot.backup_path)
    compressed_body = read_utf8(compressed_body_path)
    if original is None or compressed_body is None:
        print("REFUSED: backup or compressed body is not valid UTF-8")
        return 1
    frontmatter, original_body = split_frontmatter(original)
    if not compressed_body.strip():
        print("REFUSED: compressed body is empty")
        return 1
    if compressed_body.strip() == original_body.strip():
        print("REFUSED: output identical to input; file may already be compressed")
        return 1
    candidate = frontmatter + compressed_body
    print_format_warning(path)
    verdict = validate(original, candidate)
    for warning in verdict.warnings:
        print(f"WARNING: {warning}")
    if not verdict.is_valid:
        for error in verdict.errors:
            print(f"ERROR: {error}")
        print(
            "Target file untouched. Fix ONLY the listed errors in the compressed body"
        )
        print(
            "(restore missing content from the backup; do not recompress) and re-apply."
        )
        return 3
    write_text_atomic(path, candidate)
    pct = round(100 * (len(original) - len(candidate)) / max(len(original), 1))
    print(f"APPLIED: {path}")
    print(f"CHARS: {len(original)} -> {len(candidate)} ({pct}% smaller)")
    print(f"BACKUP: {slot.backup_path}")
    return 0


def cmd_restore(path: Path) -> int:
    path = path.resolve()
    slot = load_slot(path)
    if isinstance(slot, Refusal):
        print(f"REFUSED: {slot.reason}")
        return 1
    original = read_utf8(slot.backup_path)
    if original is None:
        print(f"REFUSED: backup is not valid UTF-8: {slot.backup_path}")
        return 1
    write_text_atomic(path, original)
    print(f"RESTORED: {path} from {slot.backup_path}")
    return 0


def tree_bytes(path: Path) -> int:
    """Total size of the regular files under a directory."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def cmd_clean(target: Path | None) -> int:
    """Delete backup artifacts. Destroys the undo; run only on explicit request."""
    if target is None:
        base = backup_base()
        if not base.is_dir():
            print("CLEAN: no backups to remove")
            return 0
        freed = tree_bytes(base)
        shutil.rmtree(base)
        print(f"CLEAN: removed the backup tree at {base} ({freed} bytes freed)")
        return 0
    slot = slot_for(target.resolve())
    recorded = recorded_source(slot)
    if recorded is not None and recorded != str(slot.source):
        print(f"REFUSED: {slot.directory} records {recorded}; not cleaning it")
        return 1
    # Remove only the artifacts this tool writes, never an arbitrary tree.
    removed = tuple(
        p for p in (slot.backup_path, slot.body_path, slot.meta_path) if p.is_file()
    )
    freed = sum(p.stat().st_size for p in removed)
    for artifact in removed:
        artifact.unlink()
        print(f"CLEAN: removed {artifact}")
    if not removed:
        print(f"CLEAN: no backups found for {target.name}")
        return 0
    print(f"CLEAN: {freed} bytes freed")
    with contextlib.suppress(OSError):  # foreign files present: leave the directory
        slot.directory.rmdir()
    return 0


# --- Self-test ---


def cmd_self_test() -> int:  # noqa: PLR0915  one linear list of invariant checks
    fm, body = split_frontmatter("---\na: 1\n---\nBody\n")
    assert fm == "---\na: 1\n---\n" and body == "Body\n"
    assert split_frontmatter("No frontmatter") == ("", "No frontmatter")
    for text in ("---\na: 1\n---\nBody\n", "No frontmatter", ""):
        assert "".join(split_frontmatter(text)) == text  # partition law

    v1, v2, v3 = Verdict.error("a"), Verdict.warning("w"), Verdict.error("b")
    assert v1.merge(Verdict.EMPTY) == v1 == Verdict.EMPTY.merge(v1)  # identity
    assert v1.merge(v2).merge(v3) == v1.merge(v2.merge(v3))  # associativity
    assert not v1.is_valid and v2.is_valid

    text = "prose\n```py\ncode\n```\ntail `x` and `x`\n~~~\nunclosed\n"
    blocks, prose = partition_fences(text)
    assert blocks == ("```py\ncode\n```",)
    assert "unclosed" in prose and "code" not in prose
    assert extract_inline_codes(text) == Counter({"x": 2})

    # CommonMark heading laws (ATX per spec; setext exists; fences excluded).
    assert extract_headings("# Real\n```sh\n# comment\n```\n") == (("#", "Real"),)
    assert extract_headings("#\nNot a title\n") == (("#", ""),)  # no newline-crossing
    assert extract_headings("   ## Indented\n") == (("##", "Indented"),)
    assert extract_headings("Title\n====\nSub\n---\n") == (("=", "Title"), ("-", "Sub"))
    assert extract_headings("para\n\n----\n") == ()  # thematic break, not setext

    # Indented code blocks are validated; list continuations are not code.
    indented_doc = "para\n\n    code\n    more\n"
    assert partition_indented(indented_doc)[0] == ("    code\n    more",)
    assert partition_indented("- item\n\n    continuation\n")[0] == ()
    assert not validate("text\n\n    code line\n", "text\n").is_valid

    nested = "````md\n```\ninner\n```\n````\n"
    assert partition_fences(nested)[0] == ("````md\n```\ninner\n```\n````",)

    good = validate("# H\nsome long prose here\n`k`\n", "# H\nprose\n`k`\n")
    assert good.is_valid
    moved_dot = validate(
        "See https://a.example/d and more\n", "See https://a.example/d.\n"
    )
    assert moved_dot.is_valid  # sentence punctuation after a URL is prose
    bad = validate("# H\ntext https://a.example\n```\nc\n```\n", "# H\ntext\n")
    assert not bad.is_valid and len(bad.errors) == 2  # noqa: PLR2004  url + code block

    assert classify(Path("Dockerfile"), None) is FileKind.CODE
    assert classify(Path("CMakeLists.txt"), None) is FileKind.CODE
    assert classify(Path("notes.md"), None) is FileKind.NATURAL_LANGUAGE
    assert classify(Path("conf.yaml"), None) is FileKind.CONFIG
    assert classify(Path("run"), "#!/bin/sh\necho hi\n") is FileKind.CODE
    assert (
        classify(Path("TODO"), "Buy milk.\nShip release.\n")
        is FileKind.NATURAL_LANGUAGE
    )

    # Classification fails closed and covers more of the language landscape.
    go = 'package main\n\nfunc main() {\n\tfmt.Println("hi")\n}\n'
    assert classify(Path("main"), go) is FileKind.CODE
    assert classify(Path("q"), "SELECT id\nFROM t;\n") is FileKind.CODE
    assert classify(Path("a.cs"), None) is FileKind.CODE
    assert classify(Path("data.csv"), None) is FileKind.CONFIG  # data, not code
    assert classify(Path(".env.local"), "A=1\n") is FileKind.CONFIG
    assert classify(Path("n"), "42") is FileKind.UNKNOWN  # bare JSON scalar
    assert classify(Path("x"), "zx9\nq7\n") is FileKind.UNKNOWN  # no prose evidence

    # Assessments are evidence, not verdicts: every non-prose guess carries
    # at least one signal, and a clean prose guess carries none.
    assert assess(Path("notes.md"), None).signals == ()
    assert assess(Path("a.py"), None).signals  # taxonomy evidence present
    inconclusive = assess(Path("x"), "zx9\nq7\n")
    assert inconclusive.kind is FileKind.UNKNOWN
    assert any("code-like" in s for s in inconclusive.signals)  # ratios stated
    for probe in (Path("a.py"), Path("conf.yaml"), Path("x")):
        # classify is the projection of assess: they can never disagree.
        assert classify(probe, "zx9\n") is assess(probe, "zx9\n").kind

    assert is_sensitive(Path("/home/u/.aws/config"))
    assert is_sensitive(Path("api-key.md"))
    assert not is_sensitive(Path("notes.md"))

    a, b = Path("/repo/docs/api/readme.md"), Path("/repo/src/api/readme.md")
    assert slot_for(a).directory != slot_for(b).directory  # injective across parents
    assert slot_for(a) == slot_for(a)  # deterministic
    long = slot_for(Path("/x/" + "n" * 300 + ".md")).directory.name
    weird = slot_for(Path("/x/notes \udcff*.md")).directory.name  # total on surrogates
    for name in (long, weird):
        assert re.fullmatch(r"[A-Za-z0-9._-]+", name)  # single safe ASCII component
        assert len(name.encode()) <= 81  # noqa: PLR2004  slug(64) + "-" + hex(16)

    print("self-test: all checks passed")
    return 0


# --- Entry point ---


def main(argv: list[str]) -> int:  # noqa: PLR0911
    # One return per verb; returns are the command interface.
    usage = (
        "Usage: compress_guard.py check|prepare|restore <file>\n"
        "       compress_guard.py apply <file> <compressed-body-file>\n"
        "       compress_guard.py clean <file> | clean --all\n"
        "       compress_guard.py self-test"
    )
    match argv:
        case ["check", target]:
            return cmd_check(Path(target))
        case ["prepare", target]:
            return cmd_prepare(Path(target))
        case ["apply", target, body]:
            return cmd_apply(Path(target), Path(body))
        case ["restore", target]:
            return cmd_restore(Path(target))
        case ["clean", "--all"]:
            return cmd_clean(None)
        case ["clean", target]:
            return cmd_clean(Path(target))
        case ["self-test"]:
            return cmd_self_test()
        case _:
            print(usage)
            return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
