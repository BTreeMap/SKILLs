"""Heuristic content assessment. Advisory only: a signal never blocks."""

from __future__ import annotations

import json
from pathlib import Path

from btm_caveman.model import Assessment, FileKind
from btm_corekit import ASCII_WORD, digit_run, keep_table, runs

COMPRESSIBLE_EXTENSIONS = frozenset(
    {".md", ".txt", ".markdown", ".rst", ".typ", ".typst", ".tex"}
)
# Compressible, but reST/LaTeX/Typst headings are invisible to the Markdown
# structural checks, so validation there is vacuous and the agent must be told.
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
WORD_CHARS = frozenset(ASCII_WORD)
NAME_CHARS = WORD_CHARS | frozenset("'")
DECLARATION_PREFIXES = (
    "import ",
    "require(",
    "const ",
    "let ",
    "var ",
    "def ",
    "class ",
    "function ",
    "async function ",
    "export ",
    "func ",
    "fn ",
    "package ",
    "module ",
    "namespace ",
    "struct ",
    "impl ",
    "trait ",
    "pub ",
)
PREPROCESSOR_WORDS = ("#include", "#define", "#pragma", "#import")
SQL_WORDS = (
    "SELECT",
    "INSERT INTO",
    "UPDATE",
    "DELETE FROM",
    "CREATE",
    "ALTER",
    "FROM",
    "WHERE",
    "JOIN",
)
CONTROL_OPENERS = ("if", "for", "while", "switch", "try")
CLOSERS = frozenset("}]);")
STATEMENT_ENDS = (";", "{", "}")
ASSIGNED_OPENERS = frozenset("{[(\"'")
PROSE_CODE_CHARS = frozenset("{};=`$<>\\")
PROSE_CODE_PAIRS = ("()", "::", "->")
MAX_INDENT = 3  # CommonMark: four spaces starts indented code
MAX_HEADING = 6
MAX_ORDERED_DIGITS = 9
MIN_WORD = 2  # letters that make a word


def _word_end(text: str, start: int) -> int:
    """Index just past the run of word characters beginning at `start`."""
    end = start
    while end < len(text) and text[end] in WORD_CHARS:
        end += 1
    return end


def _starts_with_word(text: str, words: tuple[str, ...]) -> bool:
    """`text` begins with one of `words` followed by a non-word char or the end."""
    return any(
        text.startswith(word)
        and (len(text) == len(word) or text[len(word)] not in WORD_CHARS)
        for word in words
    )


def _declares(s: str) -> bool:
    return s.startswith(DECLARATION_PREFIXES) or (
        s.startswith("from ") and " import " in s
    )


def _directive(s: str) -> bool:
    return _starts_with_word(s, PREPROCESSOR_WORDS) or _starts_with_word(s, SQL_WORDS)


def _type_signature(s: str) -> bool:
    """`name :: ...`: Haskell signatures and C++ scope resolution."""
    head, sep, _ = s.partition("::")
    name = head.strip()
    return (
        bool(sep) and bool(name) and name[0] in WORD_CHARS and set(name) <= NAME_CHARS
    )


def _control_opener(s: str) -> bool:
    for opener in CONTROL_OPENERS:
        if s.startswith(opener):
            rest = s[len(opener) :].lstrip()
            if rest.startswith("(") or (opener == "try" and rest.startswith("{")):
                return True
    return False


def _closing_or_terminated(s: str) -> bool:
    stripped = s.rstrip()
    return set(stripped) <= CLOSERS or stripped.endswith(STATEMENT_ENDS)


def _decorator(s: str) -> bool:
    return s.startswith("@") and len(s) > 1 and s[1] in WORD_CHARS


def _json_key(s: str) -> bool:
    close = s.find('"', 1) if s.startswith('"') else -1
    return close > 1 and s[close + 1 :].lstrip().startswith(":")


def _structured_assignment(s: str) -> bool:
    """`name = {` / `[` / `(` / a quote: a literal being bound."""
    name_end = _word_end(s, 0)
    after = s[name_end:].lstrip()
    return (
        bool(name_end)
        and after.startswith("=")
        and after[1:].lstrip()[:1] in ASSIGNED_OPENERS
    )


CODE_LINE_PREDICATES = (
    _declares,
    _directive,
    _type_signature,
    _control_opener,
    _closing_or_terminated,
    _decorator,
    _json_key,
    _structured_assignment,
)


def _is_code_line(line: str) -> bool:
    s = line.lstrip()
    return bool(s) and any(predicate(s) for predicate in CODE_LINE_PREDICATES)


def prose_marker_length(line: str) -> int:
    """Length of a Markdown block marker at the line start (up to three
    spaces, then `#..######`, one of `-*+>`, or `1.`/`1)`, then blank), or 0."""
    indent = len(line) - len(line.lstrip(" "))
    if indent > 3:  # noqa: PLR2004 - CommonMark's indent limit
        return 0
    rest = line[indent:]
    if rest.startswith("#"):
        hashes = len(rest) - len(rest.lstrip("#"))
        marker = hashes if 1 <= hashes <= 6 else 0  # noqa: PLR2004 - h1..h6
    elif rest[:1] in "-*+>":
        marker = 1
    else:
        digits = digit_run(rest, MAX_ORDERED_DIGITS)
        ordered = (
            1 <= digits <= MAX_ORDERED_DIGITS and rest[digits : digits + 1] in ".)"
        )
        marker = digits + 1 if ordered else 0
    if not marker or rest[marker : marker + 1] not in (" ", "\t"):
        return 0
    blank = marker
    while blank < len(rest) and rest[blank] in " \t":
        blank += 1
    return indent + blank


def _has_code_chars(text: str) -> bool:
    return not PROSE_CODE_CHARS.isdisjoint(text) or any(
        pair in text for pair in PROSE_CODE_PAIRS
    )


LETTER_TABLE = keep_table("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _count_words(text: str) -> int:
    return sum(len(word) >= MIN_WORD for word in runs(text, LETTER_TABLE))


def _is_prose_line(line: str) -> bool:
    if _is_code_line(line):
        return False
    marker = prose_marker_length(line)
    stripped = line[marker:]
    if _has_code_chars(stripped):
        return False
    return _count_words(stripped) >= (1 if marker else 2)


def _looks_like_yaml_key(stripped: str) -> bool:
    """`Key words: value` with a word-character start and a blank after the colon."""
    key, sep, rest = stripped.partition(":")
    return (
        bool(sep)
        and bool(key)
        and key[0] in WORD_CHARS
        and set("".join(key.split())) <= WORD_CHARS
        and rest[:1].isspace()
    )


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
            or _looks_like_yaml_key(stripped)
            or (stripped.startswith("- ") and ":" in stripped)
        )

    stripped_head = [s for line in lines[:30] if (s := line.strip())]
    return bool(stripped_head) and (
        sum(map(is_indicator, stripped_head)) / len(stripped_head) > 0.6  # noqa: PLR2004
    )


def assess(path: Path, text: str | None) -> Assessment:  # noqa: PLR0911
    """Assess by basename, then extension, then content (extensionless).

    Every observation becomes a signal with its evidence, never a verdict.
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
    lines = text.splitlines()[:50]
    head = [s for line in lines if (s := line.strip())]
    if not head:
        return Assessment(FileKind.UNKNOWN, ("no content to assess",))
    code_pct = round(100 * sum(map(_is_code_line, head)) / len(head))
    prose_pct = round(100 * sum(map(_is_prose_line, head)) / len(head))
    evidence = (
        f"content evidence (first {len(head)} nonblank lines):"
        f" {code_pct}% code-like, {prose_pct}% prose-like"
    )
    if _looks_like_yaml(lines[:30]):
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
