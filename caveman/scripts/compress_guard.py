#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Deterministic guard for the caveman compress mode.

The agent performs the actual prose compression; this script does everything
an LLM is bad at, deterministically:

  check <file>              classify the file; report whether it is admissible
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
"""

from __future__ import annotations

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
    reason: str


@dataclass(frozen=True, slots=True)
class Plan:
    """An admitted compression: the single trusted entry into the domain.

    `split_frontmatter` partitions the source text, so the invariant
    `original == frontmatter + body` holds by construction; nothing ever
    needs to re-read the source to recover the original.
    """

    path: Path
    frontmatter: str
    body: str

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
CONFIG_EXTENSIONS = frozenset(
    {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"}
)
CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".css",
        ".scss",
        ".html",
        ".xml",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".lua",
        ".lock",
        ".dockerfile",
        ".makefile",
        ".csv",
    }
)
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
        r"^\s*(if\s*\(|for\s*\(|while\s*\(|switch\s*\(|try\s*\{)",
        r"^\s*[\}\]\);]+\s*$",
        r"^\s*@\w+",
        r'^\s*"[^"]+"\s*:\s*',
        r"^\s*\w+\s*=\s*[{\[\(\"']",
    )
)


def _is_code_line(line: str) -> bool:
    return any(p.match(line) for p in CODE_LINE_PATTERNS)


def _looks_like_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
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


def classify(path: Path, text: str | None) -> FileKind:  # noqa: PLR0911
    """Classify by basename, then extension, then content (extensionless)."""
    # Keep one return per rule so precedence stays visible.
    if path.name.lower() in KNOWN_CODE_FILENAMES:
        return FileKind.CODE
    ext = path.suffix.lower()
    if ext in COMPRESSIBLE_EXTENSIONS:
        return FileKind.NATURAL_LANGUAGE
    if ext in CONFIG_EXTENSIONS:
        return FileKind.CONFIG
    if ext in CODE_EXTENSIONS:
        return FileKind.CODE
    if ext or text is None:
        return FileKind.UNKNOWN
    if text.startswith("#!"):
        return FileKind.CODE
    if _looks_like_json(text[:10_000]) or _looks_like_yaml(text.splitlines()[:30]):
        return FileKind.CONFIG
    lines = [s for line in text.splitlines()[:50] if (s := line.strip())]
    # Prefer prose unless code-like lines exceed 40%.
    if lines and sum(map(_is_code_line, lines)) / len(lines) > 0.4:  # noqa: PLR2004
        return FileKind.CODE
    return FileKind.NATURAL_LANGUAGE


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
HEADING_REGEX = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)
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


def extract_headings(text: str) -> tuple[tuple[str, str], ...]:
    return tuple((level, title.strip()) for level, title in HEADING_REGEX.findall(text))


def _trim_trailing_punctuation(match: str) -> str:
    """Sentence punctuation after a URL or path is prose, not address."""
    return match.rstrip(".,;:!?")


def extract_urls(text: str) -> frozenset[str]:
    return frozenset(map(_trim_trailing_punctuation, URL_REGEX.findall(text)))


def extract_paths(text: str) -> frozenset[str]:
    return frozenset(map(_trim_trailing_punctuation, PATH_REGEX.findall(text)))


def extract_inline_codes(text: str) -> Counter[str]:
    _, prose = partition_fences(text)
    return Counter(re.findall(r"`([^`]+)`", prose))


# --- Validation ---


def _check_headings(original: str, compressed: str) -> Verdict:
    orig, comp = extract_headings(original), extract_headings(compressed)
    if orig != comp:
        return Verdict.error(
            f"Headings not preserved exactly: {len(orig)} vs {len(comp)}"
        )
    return Verdict.EMPTY


def _check_code_blocks(original: str, compressed: str) -> Verdict:
    if partition_fences(original)[0] != partition_fences(compressed)[0]:
        return Verdict.error("Code blocks not preserved exactly (content and order)")
    return Verdict.EMPTY


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
    """Out-of-tree backup root so skill auto-loaders never re-ingest backups."""
    if os.name == "nt":
        base = Path(
            os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        )
    else:
        base = Path(
            os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        )
    return base / "caveman-compress" / "backups"


def artifact_paths(target: Path) -> tuple[Path, Path]:
    """(backup of the original, extracted body work file) for a target."""
    backup_dir = backup_base() / target.parent.name
    return (
        backup_dir / (target.stem + ".original.md"),
        backup_dir / (target.stem + ".body.md"),
    )


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


def admit(path: Path) -> Admission:  # noqa: PLR0911
    """Parse, don't validate: every refusal reason lives here, once."""
    # Preserve distinct refusal reasons and exit statuses.
    path = path.resolve()
    if not path.is_file():
        return Refusal(f"Not a file: {path}")
    if is_sensitive(path):
        return Refusal(
            f"Refusing {path.name}: filename looks sensitive (credentials, keys,"
            " secrets, or known private paths). Rename it if this is a false positive."
        )
    if path.name.endswith(".original.md"):
        return Refusal("Refusing to compress a backup file")
    if path.stat().st_size > MAX_FILE_SIZE:
        return Refusal(f"File exceeds {MAX_FILE_SIZE // 1000}KB; split it first")
    text = read_utf8(path)
    if text is None:
        return Refusal("File is not valid UTF-8")
    if classify(path, text) is not FileKind.NATURAL_LANGUAGE:
        return Refusal("Not natural language (code or config); nothing to compress")
    if not text.strip():
        return Refusal("File is empty or whitespace-only")
    frontmatter, body = split_frontmatter(text)
    if not body.strip():
        return Refusal("Body is empty after frontmatter removal")
    return Plan(path=path, frontmatter=frontmatter, body=body)


def cmd_check(path: Path) -> int:
    match admit(path):
        case Refusal(reason):
            print(f"REFUSED: {reason}")
            return 1
        case Plan() as plan:
            fm = "yes" if plan.frontmatter else "no"
            print(f"OK: compressible (frontmatter: {fm}, body: {len(plan.body)} chars)")
            return 0
    raise AssertionError("unreachable: Admission is a closed union")


def cmd_prepare(path: Path) -> int:
    match admit(path):
        case Refusal(reason):
            print(f"REFUSED: {reason}")
            return 1
        case Plan() as plan:
            backup_path, body_path = artifact_paths(plan.path)
            if backup_path.exists():
                print(
                    f"REFUSED: backup already exists: {backup_path}\n"
                    "Remove or restore it first; refusing to overwrite a prior "
                    "original."
                )
                return 1
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            write_text_atomic(backup_path, plan.original)
            if read_utf8(backup_path) != plan.original:
                backup_path.unlink(missing_ok=True)
                print("REFUSED: backup readback mismatch; aborting before any change")
                return 1
            write_text_atomic(body_path, plan.body)
            print(f"BACKUP: {backup_path}")
            print(f"BODY:   {body_path}")
            print(
                "Compress the BODY file's prose, then run: "
                "apply <file> <compressed-body>"
            )
            return 0
    raise AssertionError("unreachable: Admission is a closed union")


def cmd_apply(path: Path, compressed_body_path: Path) -> int:  # noqa: PLR0911
    # Preserve each refusal's contract and exit status.
    path = path.resolve()
    backup_path, _ = artifact_paths(path)
    if not backup_path.is_file():
        print(f"REFUSED: no backup found at {backup_path}; run prepare first")
        return 1
    if not compressed_body_path.is_file():
        print(f"REFUSED: compressed body not found: {compressed_body_path}")
        return 1
    original = read_utf8(backup_path)
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
    print(f"BACKUP: {backup_path}")
    return 0


def cmd_restore(path: Path) -> int:
    path = path.resolve()
    backup_path, _ = artifact_paths(path)
    if not backup_path.is_file():
        print(f"REFUSED: no backup found at {backup_path}")
        return 1
    original = read_utf8(backup_path)
    if original is None:
        print(f"REFUSED: backup is not valid UTF-8: {backup_path}")
        return 1
    write_text_atomic(path, original)
    print(f"RESTORED: {path} from {backup_path}")
    return 0


def cmd_clean(target: Path | None) -> int:
    """Delete backup artifacts. Destroys the undo; run only on explicit request."""
    if target is None:
        base = backup_base()
        if not base.is_dir():
            print("CLEAN: no backups to remove")
            return 0
        shutil.rmtree(base)
        print(f"CLEAN: removed the backup tree at {base}")
        return 0
    removed = tuple(p for p in artifact_paths(target.resolve()) if p.is_file())
    for artifact in removed:
        artifact.unlink()
        print(f"CLEAN: removed {artifact}")
    if not removed:
        print(f"CLEAN: no backups found for {target.name}")
    return 0


# --- Self-test ---


def cmd_self_test() -> int:
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

    assert is_sensitive(Path("/home/u/.aws/config"))
    assert is_sensitive(Path("api-key.md"))
    assert not is_sensitive(Path("notes.md"))

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
