"""Every subcommand names itself in `--help`; a parser without `help=` prints
a blank column beside its name. Reported, not repaired, since only the
author knows what the command does."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from btm_repo_gate.repairs import Finding
from btm_repo_gate.snapshot import Repo


def _silent_parsers(source: str) -> Iterator[tuple[int, str]]:
    """`add_parser("name")` with no `help=`, by line and name."""
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser"
            and not any(word.arg == "help" for word in node.keywords)
        ):
            first = node.args[0] if node.args else None
            name = first.value if isinstance(first, ast.Constant) else "the parser"
            yield node.lineno, str(name)


def rule_command_help(repo: Repo) -> Iterator[Finding]:
    for path in sorted(repo.texts):
        # `src/` only: a test builds throwaway parsers that no agent reads.
        if (
            path.suffix != ".py"
            or "src" not in path.parts
            or "add_parser" not in repo.texts[path]
        ):
            continue
        try:
            silent = list(_silent_parsers(repo.texts[path]))
        except SyntaxError:
            continue  # ruff owns syntax; a parse failure is its finding
        for line, name in silent:
            yield Finding(
                rule="command-help",
                path=f"{path}:{line}",
                message=f"subcommand {name!r} has no help=; --help prints it blank",
            )
