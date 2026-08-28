"""btm-corekit: the shared symbolic kernel for SKILLs bundled scripts.

Single definition of the identifier algebra, the stdout/stderr channel
convention, atomic writes, JSONL containers, the request-identity chain,
the session store, and the CLI error boundary. Consumers declare this
package as a workspace dependency, so a skill runs from a full repository
checkout and a script copied out alone fails loudly at environment build.

Purity split: identifier functions are pure except `suffix`/`mint`
(randomness); everything past the channels section reads or writes the
environment, filesystem, or process streams.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

KEYWORD_RANGE = (2, 3)  # advisory band for minting keywords
NON_SLUG = re.compile(r"[^a-z0-9]+")
USER_AGENT_ENV = "BTM_USER_AGENT"
CONTACT_ENV = "BTM_CONTACT"
DEFAULT_CONTACT = "skills@oss.joefang.org"


class CommandError(Exception):
    """Failure that ends a command with a clean message and exit code 1."""


# --- identifiers: pure ---


def keywords_of(text: str) -> list[str]:
    return [part for part in NON_SLUG.sub("-", text.lower()).split("-") if part]


def slugify(words: Iterable[str]) -> str:
    cleaned = [part for word in words for part in keywords_of(str(word))]
    if not cleaned:
        raise CommandError("identifier keywords must contain letters or digits")
    return "-".join(cleaned)


def band_signal(stem: str) -> str | None:
    """Advisory for a stem outside the keyword band; None inside it."""
    low, high = KEYWORD_RANGE
    if low <= stem.count("-") + 1 <= high:
        return None
    return f"'{stem}': two or three keywords resolve best"


@dataclass(frozen=True, slots=True)
class Exact:
    id: str


@dataclass(frozen=True, slots=True)
class Recovered:
    id: str


@dataclass(frozen=True, slots=True)
class Ambiguous:
    candidates: tuple[str, ...]  # sorted


@dataclass(frozen=True, slots=True)
class NoMatch:
    pass


Resolution = Exact | Recovered | Ambiguous | NoMatch


def resolve(ref: str, ids: Iterable[str]) -> Resolution:
    """Total resolution: exact id, else the id containing every keyword.

    O(ids x keywords); pools stay in the low hundreds.
    """
    pool = list(ids)
    if ref in pool:
        return Exact(ref)
    keywords = keywords_of(ref)
    matches = [
        candidate
        for candidate in pool
        if keywords and all(keyword in candidate for keyword in keywords)
    ]
    if not matches:
        return NoMatch()
    if len(matches) > 1:
        return Ambiguous(tuple(sorted(matches)))
    return Recovered(matches[0])


def eliminate(
    resolution: Resolution, ref: str, kind: str, hint: str | None = None
) -> tuple[str, str | None]:
    """Eliminate a Resolution into (identifier, recovery signal or None).

    Raises CommandError on Ambiguous and NoMatch; `hint` extends the
    NoMatch message with the command that creates the missing subject.
    """
    match resolution:
        case Exact(full):
            return full, None
        case Recovered(full):
            return full, f"recovered {kind} '{ref}' -> {full}; use the full identifier"
        case Ambiguous(candidates):
            raise CommandError(
                f"'{ref}' is ambiguous across {kind}s: {', '.join(candidates)}"
            )
        case NoMatch() if not keywords_of(ref):
            raise CommandError(f"empty {kind} reference")
        case NoMatch():
            tail = f"; {hint}" if hint else ""
            raise CommandError(f"no {kind} matches '{ref}'{tail}")
    raise AssertionError("unreachable: Resolution is a closed union")


def suffix() -> str:
    """128 bits of entropy, base32hex, lowercase: uniqueness is the script's job."""
    return base64.b32hexencode(os.urandom(16)).decode().rstrip("=").lower()


def mint(words: Iterable[str]) -> str:
    return f"{slugify(words)}-{suffix()}"


def is_pathlike(argument: str) -> bool:
    return (
        os.sep in argument
        or (os.altsep is not None and os.altsep in argument)
        or argument.startswith(("~", "."))
    )


# --- channels: one JSON document on stdout, advisories on stderr ---


def emit(document: Mapping[str, Any]) -> None:
    print(json.dumps(document, indent=2, ensure_ascii=False))


def signal(message: str) -> None:
    print(f"signal: {message}", file=sys.stderr)


# --- clock ---


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --- filesystem ---


def state_root(skill: str) -> Path:
    """Durable-state home for one skill, per repository convention."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    else:
        base = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
    return Path(base) / "btm-skills" / skill


def tree_bytes(path: Path) -> int:
    """Total size of the regular files under a directory."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def write_atomic(path: Path, text: str) -> None:
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def append_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    """One record is a batch of one."""
    payload = "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload)


# --- request identity: BTM_USER_AGENT, else BTM_CONTACT, else the project contact ---


@dataclass(frozen=True, slots=True)
class CustomAgent:
    header: str


@dataclass(frozen=True, slots=True)
class Contact:
    address: str


RequestIdentity = CustomAgent | Contact


def request_identity() -> RequestIdentity:
    custom = os.environ.get(USER_AGENT_ENV)
    if custom:
        return CustomAgent(custom)
    return Contact(os.environ.get(CONTACT_ENV) or DEFAULT_CONTACT)


def user_agent(skill: str) -> str:
    match request_identity():
        case CustomAgent(header):
            return header
        case Contact(address):
            return f"btm-skills/1.0 ({skill}; mailto:{address})"


def polite_params() -> dict[str, str]:
    """The `mailto` pool parameter OpenAlex and Crossref honor. Empty under a
    User-Agent override: the override owns identity, so nothing else marks
    the request."""
    match request_identity():
        case CustomAgent():
            return {}
        case Contact(address):
            return {"mailto": address}


# --- session store: one layout for every session-keeping skill ---


@dataclass(frozen=True, slots=True)
class SessionStore:
    """Sessions under the skill's state root; `marker` witnesses a session,
    `hint` names the command that creates one."""

    skill: str
    marker: str
    hint: str

    def root(self) -> Path:
        return state_root(self.skill) / "sessions"

    def ids(self) -> list[str]:
        root = self.root()
        if not root.exists():
            return []
        return sorted(entry.name for entry in root.iterdir() if entry.is_dir())

    def dir_of(self, ref: str) -> Path:
        """A path argument stands as given; anything else resolves against
        `ids()`, rendering the recovery signal."""
        if is_pathlike(ref):
            return Path(ref).expanduser()
        full, note = eliminate(resolve(ref, self.ids()), ref, "session", hint=self.hint)
        if note:
            signal(note)
        return self.root() / full

    def clean(self, ref: str | None, remove_all: bool) -> dict[str, Any]:
        """List sessions with sizes, or remove one session or the whole root,
        reporting bytes freed. Removal demands the marker: never an arbitrary
        tree."""
        root = self.root()
        if remove_all and ref:
            raise CommandError("pass a session or --all, one of the two")
        if remove_all:
            if not root.is_dir():
                return {"removed": None, "bytes_freed": 0}
            freed = tree_bytes(root)
            shutil.rmtree(root)
            return {"removed": str(root), "bytes_freed": freed}
        if ref is None:
            listing = (
                [
                    {"session": entry.name, "bytes": tree_bytes(entry)}
                    for entry in sorted(root.iterdir())
                    if entry.is_dir()
                ]
                if root.is_dir()
                else []
            )
            return {
                "sessions_root": str(root),
                "sessions": listing,
                "next": "pass a session identifier or --all to remove and free space",
            }
        target = self.dir_of(ref)
        if not (target / self.marker).is_file():
            raise CommandError(
                f"{target} holds no session ({self.marker} absent); refusing to remove"
            )
        freed = tree_bytes(target)
        shutil.rmtree(target)
        return {"removed": str(target), "bytes_freed": freed}


# --- cli boundary ---


def run_cli(parser: argparse.ArgumentParser, argv: Sequence[str] | None = None) -> int:
    """Dispatch to the parsed `func`, turning CommandError into exit 1."""
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CommandError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
