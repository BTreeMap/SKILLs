"""Single definition: a consumer may depend on the kernel, never redefine it."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from btm_repo_gate.conventions import KERNEL
from btm_repo_gate.repairs import Finding, RemovePath
from btm_repo_gate.snapshot import Absent, LinkFarm, Occupied, Repo, Symlink

KERNEL_FUNCTIONS = frozenset(
    {
        "keywords_of",
        "slugify",
        "band_signal",
        "resolve",
        "eliminate",
        "mint",
        "suffix",
        "is_pathlike",
        "tree_bytes",
        "state_root",
        "emit",
        "signal",
        "now_iso",
        "write_atomic",
        "read_jsonl",
        "append_jsonl",
        "request_identity",
        "user_agent",
        "polite_params",
        "run_cli",
        "jot",
        "recall",
        "pad_body",
        "pad_entries",
        "pad_ids",
        "require",
        "parse_enum",
        "parse_model",
        "field_text",
        "suggest",
        "read_batch",
        "read_count",
        "read_opt_text",
        "read_text",
        "read_texts",
        "refuse",
        "where_of",
        "read_payload",
        "sole_source",
        "rejection",
        "advise",
        "wire_pad",
        "wire_clean",
        "compile_match",
        "ascii_words",
        "bracketed",
        "collapse_whitespace",
        "demand",
        "gated",
        "diagnostics",
        "digest",
        "dump",
        "digit_run",
        "heading_words",
        "is_digits",
        "prefixed_number",
        "strip_tags",
        "keep_table",
        "runs",
    }
)
KERNEL_CLASSES = frozenset(
    {
        "Exact",
        "Recovered",
        "Ambiguous",
        "NoMatch",
        "CommandError",
        "UpstreamError",
        "SessionStore",
        "CustomAgent",
        "Contact",
        "Diagnostic",
        "Admission",
        "Pool",
        "EventLog",
        "Created",
        "Cluster",
        "Digest",
        "Item",
        "Model",
        "Outcome",
        "Inline",
        "FromFile",
        "FromStdin",
        "Payload",
    }
)
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


def redefined_kernel_symbols(text: str) -> Iterator[str]:
    """Top-level definitions that shadow a kernel name. Two C-level substring
    tests skip a file that defines nothing, so most files never split."""
    if "def " not in text and "class " not in text:
        return
    for line in text.split("\n"):
        if (name := _defined_name(line, "def ")) and name in KERNEL_FUNCTIONS:
            if line[len("def ") + len(name) :].startswith("("):
                yield f"def {name}("
        elif (name := _defined_name(line, "class ")) and name in KERNEL_CLASSES:
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
        for found in redefined_kernel_symbols(repo.texts[path]):
            yield Finding(
                "kernel",
                str(path),
                f"kernel symbol redefined in a consumer: {found}",
            )
