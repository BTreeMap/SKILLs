"""Heuristic content assessment. Advisory only: a signal never blocks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from btm_caveman.model import Assessment, FileKind

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
