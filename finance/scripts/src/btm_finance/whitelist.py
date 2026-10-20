"""The AST whitelist for `signal.py`: imports from a fixed list, no file,
network, or reflection builtins, no file-reading attributes, no dunder names,
nothing of `btm_finance` but `api.Market`. Checked before any import.

The bytes checked are the bytes executed: the module is compiled from the
audited source under a fresh name, never re-read from disk.
"""

from __future__ import annotations

import ast
import importlib.util
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from btm_corekit import CommandError

ALLOWED = frozenset(
    {
        "numpy",
        "math",
        "statistics",
        "itertools",
        "functools",
        "operator",
        "collections",
        "dataclasses",
        "typing",
    }
)
API = "btm_finance.api"
PACKAGE, MODULE, CLASS = "btm_finance", "api", "Market"
REFUSED = frozenset(
    {
        "open",
        "eval",
        "exec",
        "compile",
        "__import__",
        "globals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "breakpoint",
    }
)
READERS = frozenset(
    {
        "load",
        "fromfile",
        "loadtxt",
        "genfromtxt",
        "memmap",
        "DataSource",
        "save",
        "savez",
        "savez_compressed",
        "savetxt",
        "lib",
        "ctypeslib",
        "f2py",
        "testing",
        "distutils",
    }
)
"""Attribute names that read or write files, reach the network, or open a way
past the list: refused on any object."""
ENTRY = "signal"
Signal = Callable[[Any, Mapping[str, float]], Any]


@dataclass(frozen=True, slots=True)
class Refusal:
    """One refused node, by file and 1-based line."""

    file: str
    line: int
    node: str

    def text(self) -> str:
        return f"{self.file}:{self.line}: refused {self.node}"


def dunder(name: str | None) -> bool:
    return name is not None and name.startswith("__")


def import_refusals(node: ast.Import) -> Iterator[str]:
    for alias in node.names:
        if alias.name.split(".")[0] not in ALLOWED:
            yield f"import {alias.name}"
        if dunder(alias.asname):
            yield f"alias {alias.asname}"


def from_refusals(node: ast.ImportFrom) -> Iterator[str]:
    module = node.module or ""
    names = [alias.name for alias in node.names]
    shown = f"from {'.' * node.level}{module} import {', '.join(names)}"
    if node.level:
        yield f"relative {shown}"
    elif "*" in names:
        yield f"{shown} (import *)"
    elif module == PACKAGE:
        yield from (f"from {PACKAGE} import {n}" for n in names if n != MODULE)
    elif module == API:
        yield from (f"from {API} import {n}" for n in names if n != CLASS)
    elif module.split(".")[0] not in ALLOWED:
        yield shown
    yield from (f"alias {a.asname}" for a in node.names if dunder(a.asname))


def api_names(tree: ast.AST) -> frozenset[str]:
    """Names `from btm_finance import api [as x]` binds, `api` always."""
    bound = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == PACKAGE
        for alias in node.names
    }
    return frozenset(bound | {MODULE})


def attribute_refusals(node: ast.Attribute, apis: frozenset[str]) -> Iterator[str]:
    """Readers anywhere; nothing on `btm_finance`; only `Market` on `api`."""
    if dunder(node.attr) or node.attr in READERS:
        yield f"attribute .{node.attr}"
    match node.value:
        case ast.Name(id=name) if name == PACKAGE:
            yield f"attribute {PACKAGE}.{node.attr}"
        case ast.Name(id=name) if name in apis and node.attr != CLASS:
            yield f"attribute {name}.{node.attr}"
        case _:
            return


def node_refusals(node: ast.AST, apis: frozenset[str]) -> Iterator[str]:
    """What one node breaks; most nodes break nothing."""
    match node:
        case ast.Import():
            yield from import_refusals(node)
        case ast.ImportFrom():
            yield from from_refusals(node)
        case ast.Name(id=name) if name in REFUSED or dunder(name):
            yield f"name {name}"
        case ast.Attribute():
            yield from attribute_refusals(node, apis)
        case (
            ast.FunctionDef(name=name)
            | ast.AsyncFunctionDef(name=name)
            | ast.ClassDef(name=name)
        ) if dunder(name):
            yield f"definition {name}"
        case ast.arg(arg=name) if dunder(name):
            yield f"argument {name}"
        case ast.keyword(arg=name) if dunder(name):
            yield f"keyword {name}"
        case ast.Global(names=names) | ast.Nonlocal(names=names):
            yield from (f"name {n}" for n in names if n in REFUSED or dunder(n))
        case _:
            return


def screen(source: str, file: str) -> list[Refusal]:
    """Every refused node in file order; a syntax error is one refusal. O(nodes)."""
    try:
        tree = ast.parse(source, filename=file)
    except SyntaxError as err:
        return [Refusal(file, err.lineno or 0, f"syntax: {err.msg}")]
    apis = api_names(tree)
    found = [
        Refusal(file, getattr(node, "lineno", 0), text)
        for node in ast.walk(tree)
        for text in node_refusals(node, apis)
    ]
    return sorted(found, key=lambda refusal: (refusal.line, refusal.node))


def load_signal(source: str, file: str, module_name: str) -> Signal:
    """The audited source's `signal`, compiled and run as a fresh module;
    every refusal raised at once, before any of it runs."""
    refusals = screen(source, file)
    if refusals:
        raise CommandError(
            "signal.py fails the whitelist; fix each node:\n"
            + "\n".join(refusal.text() for refusal in refusals)
        )
    spec = importlib.util.spec_from_loader(module_name, loader=None, origin=file)
    if spec is None:  # pragma: no cover - spec_from_loader returns a spec here
        raise CommandError(f"cannot make a module for {file}")
    module = importlib.util.module_from_spec(spec)
    try:
        exec(compile(source, file, "exec"), vars(module))  # audited above
    except Exception as err:  # any failure is the strategy's
        raise CommandError(f"{file} failed on import: {err!r}") from err
    found = vars(module).get(ENTRY)
    if not callable(found):
        raise CommandError(f"{file} defines no {ENTRY}(market, params)")
    entry: Signal = found
    return entry
