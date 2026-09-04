"""The closed plan-step ADT.

A Plan is a sorted tuple of these values. Every variant is frozen and
hashable, so identical requirements from different recipes deduplicate by
value, and the plan is a deterministic function of (spec, host).

Stages impose the only ordering that matters; within a stage, steps sort by
their stable string key. The executor for each variant lives in `effects`;
this module stays pure data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from .model import CondaPlatform


class ArchiveKind(StrEnum):
    """How a fetched artifact is materialized."""

    ZIP = "zip"
    TAR = "tar"
    BIN = "bin"


class Stage(IntEnum):
    BOOTSTRAP = 0  # micromamba
    TOOLCHAIN = 1  # conda prefixes and uv venv
    FETCH = 2  # publisher archives
    SHIM = 3  # wrappers over stages 1-2
    ASSEMBLE = 4  # installers over stages 1-3
    BIND = 5  # project-adjacent config


@dataclass(frozen=True, slots=True)
class CondaEnv:
    """One conda prefix, created by ONE micromamba call. micromamba create
    replaces a prefix rather than adding to it, so the planner merges every
    package bound for the same prefix into a single step; a second create
    against one prefix is unrepresentable in a valid plan."""

    prefix_rel: str  # e.g. "conda/host"
    platform: CondaPlatform | None  # None means host platform
    packages: tuple[str, ...]  # sorted specs


@dataclass(frozen=True, slots=True)
class UvVenv:
    """A uv-managed CPython plus a venv, both inside the root. uv is the
    supplier: no conda involvement for pure-python specs."""

    version: str | None


@dataclass(frozen=True, slots=True)
class Fetch:
    """Download-and-materialize from a publisher. An archive extracts into
    dest with `strip` leading components dropped; a binary installs itself,
    executable."""

    name: str
    url: str
    sha256: str | None  # None means no stable publisher digest
    kind: ArchiveKind
    dest_rel: str
    strip: int = 0


@dataclass(frozen=True, slots=True)
class GhcupToolchain:
    """Drive a fetched ghcup binary to install ghc + cabal under the root."""

    ghc: str  # version or recommended


@dataclass(frozen=True, slots=True)
class AndroidSdk:
    """sdkmanager-driven SDK provisioning: licenses, platform, build-tools."""

    api: int


@dataclass(frozen=True, slots=True)
class Aapt2Shim:
    """Google ships linux aapt2 as x86_64 only; every Android resource task
    runs it. Materialize the aapt2 AGP itself would resolve, wrap it in the
    emulator, and register the wrapper via android.aapt2FromMavenOverride in
    the isolated gradle.properties. Only planned when emulation() says the
    host cannot execute it natively."""

    qemu_binary: str  # emulator in the host prefix
    sysroot_platform: CondaPlatform


@dataclass(frozen=True, slots=True)
class CompilerShims:
    """conda-forge compilers carry triple-prefixed names. Fixed-name shims
    (cc, c++, gcc, g++) let CC/CXX be known at plan time and let configure
    scripts find a compiler without guessing the triple."""


@dataclass(frozen=True, slots=True)
class UvShim:
    """Link the host uv into the shims dir so the activated PATH, which drops
    the caller's PATH, still reaches it."""


@dataclass(frozen=True, slots=True)
class BindGradleProject:
    """Write sdk.dir into the project's ignored local.properties, which
    overrides SDK env vars and therefore must never go stale."""


Step = (
    CondaEnv
    | UvVenv
    | Fetch
    | GhcupToolchain
    | AndroidSdk
    | Aapt2Shim
    | CompilerShims
    | UvShim
    | BindGradleProject
)


def stage_of(step: Step) -> Stage:
    """Exhaustive over the closed sum, so a new variant is a type error here
    rather than a KeyError at sort time. The dict this replaces was keyed by
    type: it type-checked everywhere and failed only once a plan was built."""
    match step:
        case CondaEnv() | UvVenv():
            return Stage.TOOLCHAIN
        case Fetch():
            return Stage.FETCH
        case Aapt2Shim() | CompilerShims() | UvShim():
            return Stage.SHIM
        case GhcupToolchain() | AndroidSdk():
            return Stage.ASSEMBLE
        case BindGradleProject():
            return Stage.BIND


def sort_key(step: Step) -> tuple[int, str, str]:
    return (stage_of(step), type(step).__name__, repr(step))
