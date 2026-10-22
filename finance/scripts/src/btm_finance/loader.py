"""Load `strategies/<name>/signal.py` with the strategy folder and the book
root importable, and list what it imports from outside the book.

`signal.py` defines `signal(market, params)`: `market` a `Market`, `params`
the `config.json` `params`; it returns target weights by name, and a name it
omits weighs zero. It may import the book's `lib/` (`import lib.<module>`),
helpers in its strategy folder, and any installed module, at module top or
inside a function; no import is refused, and every call of `signal` runs
with the same paths. It reads prices and fundamentals only through
`market`.

`imports`: sorted top-level names that import statements reach in
`signal.py` and, recursively, in every book-local module it imports (under
`lib/` or the strategy folder). Left out: standard library, `numpy`,
`btm_finance.api` with `Market`, book-local modules. Any other api name
reached is listed as `btm_finance.api.<name>`; another `btm_finance` module
as `btm_finance.<module>`. `modules`: the book-local files reached, paths
relative to the book root, which `measure` hashes into `code_files`.
"""

from __future__ import annotations

import ast
import importlib.util
import secrets
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from btm_corekit import CommandError

ENTRY = "signal"
LIB = "lib"
PACKAGE, MODULE, CLASS = "btm_finance", "api", "Market"
API = f"{PACKAGE}.{MODULE}"
SILENT = frozenset(sys.stdlib_module_names) | {"numpy"}
Signal = Callable[[Any, Mapping[str, float]], Any]


@dataclass(frozen=True, slots=True)
class Loaded:
    """The strategy's entry point and what it imports from outside the book."""

    signal: Signal
    imports: tuple[str, ...]
    modules: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Reach:
    """What `signal.py` reaches: outside names, and book-local files by
    path relative to the book root."""

    imports: tuple[str, ...]
    modules: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Source:
    """One parsed file and its dotted module name; `signal.py` has none."""

    path: Path
    name: str | None
    package: bool
    tree: ast.Module


@dataclass(frozen=True, slots=True)
class Roots:
    """Where book-local modules live: the strategy folder first, then `lib/`
    under the book root; the order `sys.path` searches them."""

    book: Path
    folder: Path

    def file_of(self, dotted: str) -> tuple[Path, bool] | None:
        """The file of a book-local module and whether it is a package."""
        parts = dotted.split(".")
        bases = [self.folder, *([self.book] if parts[0] == LIB else [])]
        for base in bases:
            stem = base.joinpath(*parts)
            if (stem / "__init__.py").is_file():
                return stem / "__init__.py", True
            if stem.with_suffix(".py").is_file():
                return stem.with_suffix(".py"), False
        return None

    def local(self, top: str) -> bool:
        """A top-level name the strategy folder or `lib/` holds, as module,
        package, or namespace directory."""
        homes = [self.folder / top, *([self.book / LIB] if top == LIB else [])]
        return any(home.is_dir() or home.with_suffix(".py").is_file() for home in homes)

    def local_names(self) -> frozenset[str]:
        """Top-level names a book-local module can take; `signal` excluded,
        since the strategy folder would otherwise shadow the stdlib module."""
        found = {
            path.stem if path.suffix == ".py" else path.name
            for path in self.folder.iterdir()
            if path.suffix == ".py" or (path / "__init__.py").is_file()
        }
        return frozenset((found - {ENTRY}) | {LIB})


def parse(path: Path, name: str | None, package: bool) -> Source:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, SyntaxError, ValueError) as err:
        raise CommandError(f"{path} does not parse: {err}") from err
    return Source(path, name, package, tree)


def parents(dotted: str) -> list[str]:
    """`a.b.c` to `a`, `a.b`, `a.b.c`: importing one runs each package."""
    parts = dotted.split(".")
    return [".".join(parts[: i + 1]) for i in range(len(parts))]


def absolute(source: Source, node: ast.ImportFrom) -> str | None:
    """The module a relative import names; None from `signal.py`, which has
    no package."""
    if not node.level:
        return node.module
    if source.name is None:
        return None
    parts = source.name.split(".")
    base = parts if source.package else parts[:-1]
    kept = base[: len(base) - (node.level - 1)]
    return ".".join([*kept, *([node.module] if node.module else [])]) or None


def outside(dotted: str, names: Iterable[str]) -> Iterator[str]:
    """What one absolute import lists, book-local modules aside."""
    top = dotted.split(".", maxsplit=1)[0]
    if top == PACKAGE:
        if dotted == PACKAGE:
            yield from (f"{PACKAGE}.{n}" for n in names if n != MODULE)
            if not names:
                yield PACKAGE
        elif dotted == API or dotted.startswith(f"{API}."):
            yield from (f"{API}.{n}" for n in names if n != CLASS)
        else:
            yield ".".join(dotted.split(".")[:2])
    elif top not in SILENT:
        yield top


def api_aliases(tree: ast.AST) -> frozenset[str]:
    """Names bound to the api module: `from btm_finance import api [as a]`,
    `import btm_finance.api as a`."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == PACKAGE:
            found |= {a.asname or a.name for a in node.names if a.name == MODULE}
        elif isinstance(node, ast.Import):
            found |= {a.asname for a in node.names if a.name == API and a.asname}
    return frozenset(found)


def api_reach(tree: ast.AST) -> Iterator[str]:
    """Each api attribute but `Market` the code reads off the module."""
    aliases = api_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or node.attr == CLASS:
            continue
        match node.value:
            case ast.Name(id=name) if name in aliases:
                yield f"{API}.{node.attr}"
            case ast.Attribute(value=ast.Name(id=root), attr=attr) if (
                root == PACKAGE and attr == MODULE
            ):
                yield f"{API}.{node.attr}"
            case _:
                continue


def reached(source: Source, roots: Roots) -> tuple[set[str], list[str]]:
    """One file: names listed, and book-local modules to walk next."""
    listed: set[str] = set(api_reach(source.tree))
    local: list[str] = []
    pairs: list[tuple[str, tuple[str, ...]]]
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Import):
            pairs = [(alias.name, ()) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = absolute(source, node)
            if module is None:
                continue
            names = tuple(alias.name for alias in node.names)
            pairs = [(module, names)]
            local += [f"{module}.{n}" for n in names if roots.file_of(f"{module}.{n}")]
        else:
            continue
        for dotted, names in pairs:
            if roots.local(top(dotted)):
                local += parents(dotted)
            else:
                listed |= set(outside(dotted, names))
    return listed, local


def reach_of(signal_file: Path, roots: Roots) -> Reach:
    """Walk `signal.py` and every book-local module it reaches, each once.
    O(total AST nodes)."""
    queue = [parse(signal_file, None, package=False)]
    seen: set[str] = set()
    files: set[str] = set()
    listed: set[str] = set()
    while queue:
        found, local = reached(queue.pop(), roots)
        listed |= found
        for dotted in local:
            hit = roots.file_of(dotted)
            if dotted in seen or hit is None:
                continue
            seen.add(dotted)
            files.add(hit[0].resolve().relative_to(roots.book).as_posix())
            queue.append(parse(hit[0], dotted, package=hit[1]))
    return Reach(tuple(sorted(listed)), tuple(sorted(files)))


def roots_of(book: Path, name: str) -> Roots:
    return Roots(book.resolve(), (book / "strategies" / name).resolve())


def strategy_reach(book: Path, name: str) -> Reach:
    """`reach_of` for `strategies/<name>/signal.py`, running none of it."""
    roots = roots_of(book, name)
    return reach_of(roots.folder / "signal.py", roots)


def top(name: str) -> str:
    return name.partition(".")[0]


@contextmanager
def importable(roots: Roots) -> Iterator[None]:
    """Strategy folder, then book root, first on `sys.path`; modules under
    book-local names stashed before and dropped after, so no two books or
    strategies share one."""
    local = roots.local_names()
    shadowed = {n: sys.modules.pop(n) for n in list(sys.modules) if top(n) in local}
    saved = list(sys.path)
    sys.path[:0] = [str(roots.folder), str(roots.book)]
    try:
        yield
    finally:
        sys.path[:] = saved
        for name in [n for n in sys.modules if top(n) in local]:
            del sys.modules[name]
        sys.modules.update(shadowed)


def load_strategy(book: Path, name: str) -> Loaded:
    """`strategies/<name>/signal.py` run as a fresh module; its `signal` and
    `imports`. Any failure on import is the strategy's, named by file."""
    roots = roots_of(book, name)
    path = roots.folder / "signal.py"
    shown = f"strategies/{name}/signal.py"
    if not path.is_file():
        raise CommandError(f"no {shown} in the book")
    reach = reach_of(path, roots)
    module_name = f"btm_strategy_{name.replace('-', '_')}_{secrets.token_hex(4)}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - a .py file
        raise CommandError(f"cannot make a module for {shown}")
    module = importlib.util.module_from_spec(spec)
    with importable(roots):
        try:
            spec.loader.exec_module(module)
        except Exception as err:  # any failure is the strategy's
            raise CommandError(f"{shown} failed on import: {err!r}") from err
    found = vars(module).get(ENTRY)
    if not callable(found):
        raise CommandError(f"{shown} defines no {ENTRY}(market, params)")
    entry: Signal = found
    return Loaded(guarded(entry, roots), reach.imports, reach.modules)


def guarded(entry: Signal, roots: Roots) -> Signal:
    """`entry` with every call inside `importable(roots)`, so an import in a
    function body finds this book's modules and leaves none behind."""

    def call(market: Any, params: Mapping[str, float]) -> Any:
        with importable(roots):
            return entry(market, params)

    return call
