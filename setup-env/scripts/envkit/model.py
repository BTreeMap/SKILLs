"""Pure domain model: hosts, platforms, tags, layout, env deltas, emulation.

Two boundaries admit untrusted values into this domain, and both parse rather
than validate: `detect_host` (uname facts) and `parse_tag` (user-typed tags).
Everything else is a total function over already-trusted values.
"""
from __future__ import annotations

import hashlib
import os
import platform as _platform
import re
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DenvError(Exception):
    """The one error channel. Raised with a complete, actionable message;
    the CLI renders str(error) and exits nonzero. Nothing else escapes."""


# --- Host ---------------------------------------------------------------------


class OS(Enum):
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class Arch(Enum):
    X86_64 = "x86_64"
    ARM64 = "arm64"


class CondaPlatform(Enum):
    """conda-forge subdirectories: the vocabulary micromamba speaks."""

    LINUX_64 = "linux-64"
    LINUX_AARCH64 = "linux-aarch64"
    OSX_64 = "osx-64"
    OSX_ARM64 = "osx-arm64"
    WIN_64 = "win-64"


_CONDA_OF: dict[tuple[OS, Arch], CondaPlatform] = {
    (OS.LINUX, Arch.X86_64): CondaPlatform.LINUX_64,
    (OS.LINUX, Arch.ARM64): CondaPlatform.LINUX_AARCH64,
    (OS.MACOS, Arch.X86_64): CondaPlatform.OSX_64,
    (OS.MACOS, Arch.ARM64): CondaPlatform.OSX_ARM64,
    (OS.WINDOWS, Arch.X86_64): CondaPlatform.WIN_64,
}


@dataclass(frozen=True, slots=True)
class Host:
    os: OS
    arch: Arch

    @property
    def conda_platform(self) -> CondaPlatform:
        # Total: detect_host admits only keys of _CONDA_OF.
        return _CONDA_OF[(self.os, self.arch)]

    def __str__(self) -> str:
        return f"{self.os.value}/{self.arch.value}"


def detect_host() -> Host:
    """Parse uname facts into the closed host set, or stop with a real answer."""
    system = _platform.system()
    machine = _platform.machine().lower()
    os_ = {"Linux": OS.LINUX, "Darwin": OS.MACOS, "Windows": OS.WINDOWS}.get(system)
    arch = {
        "x86_64": Arch.X86_64,
        "amd64": Arch.X86_64,
        "aarch64": Arch.ARM64,
        "arm64": Arch.ARM64,
    }.get(machine)
    if os_ is None or arch is None:
        raise DenvError(f"unsupported host {system}/{machine}; "
                        "supported: linux/macos/windows on x86_64/arm64")
    if (os_, arch) not in _CONDA_OF:
        raise DenvError(f"unsupported host {system}/{machine}; "
                        "windows/arm64 has no toolchain coverage yet - use WSL")
    return Host(os_, arch)


# --- Emulation: the one architecture fact, generalized ------------------------
#
# Some publishers ship a tool for exactly one platform. How a host reaches a
# binary of platform `needed` is a total function of (host, needed), decided
# here and nowhere else. Downstream code branches on the answer's variant,
# never on the architecture.


@dataclass(frozen=True, slots=True)
class Native:
    """The host executes the binary directly."""


@dataclass(frozen=True, slots=True)
class QemuUser:
    """linux only: qemu user-mode emulation plus a sysroot of the foreign
    architecture for the dynamic linker to resolve libraries in."""

    qemu_package: str      # conda-forge package providing the emulator
    qemu_binary: str       # its executable name inside the host prefix
    sysroot_package: str   # conda-forge sysroot package for `needed`


@dataclass(frozen=True, slots=True)
class Rosetta:
    """macos/arm64 runs osx-64 binaries transparently once Rosetta 2 is
    installed (softwareupdate --install-rosetta). No wrapper required."""


@dataclass(frozen=True, slots=True)
class Unsupported:
    reason: str


Emulation = Native | QemuUser | Rosetta | Unsupported

_QEMU_FOR: dict[CondaPlatform, QemuUser] = {
    CondaPlatform.LINUX_64: QemuUser(
        "qemu-execve-x86_64", "qemu-x86_64", "sysroot_linux-64"),
    CondaPlatform.LINUX_AARCH64: QemuUser(
        "qemu-execve-aarch64", "qemu-aarch64", "sysroot_linux-aarch64"),
}


def emulation(host: Host, needed: CondaPlatform) -> Emulation:
    if host.conda_platform == needed:
        return Native()
    match host.os:
        case OS.LINUX if needed in _QEMU_FOR:
            return _QEMU_FOR[needed]
        case OS.MACOS if (host.arch, needed) == (Arch.ARM64, CondaPlatform.OSX_64):
            return Rosetta()
        case _:
            return Unsupported(
                f"host {host} cannot execute {needed.value} binaries: "
                "qemu user-mode emulation exists only on linux")


# --- Tags ---------------------------------------------------------------------
#
# Grammar:  tag := family [":" flavor] ["@" version]
#
# family selects a toolchain, flavor selects what it builds FOR (default
# "generic"), version pins the toolchain. The axes are orthogonal: the catalog
# is keyed by (family, flavor) and version is a parameter of the recipe.

_TAG_RE = re.compile(
    r"^(?P<family>[a-z][a-z0-9+]*)"
    r"(?::(?P<flavor>[a-z][a-z0-9-]*))?"
    r"(?:@(?P<version>[A-Za-z0-9][A-Za-z0-9._-]*))?$")

GENERIC = "generic"

RecipeKey = tuple[str, str]  # (family, flavor), post-alias, catalog-closed


@dataclass(frozen=True, slots=True)
class Target:
    """A parsed, catalog-validated tag. Constructed only by catalog.resolve."""

    key: RecipeKey
    version: str | None

    def __str__(self) -> str:
        family, flavor = self.key
        tag = family if flavor == GENERIC else f"{family}:{flavor}"
        return tag if self.version is None else f"{tag}@{self.version}"


@dataclass(frozen=True, slots=True)
class RawTag:
    """A syntactically valid tag, not yet checked against the catalog."""

    family: str
    flavor: str
    version: str | None


def parse_tag(text: str) -> RawTag:
    m = _TAG_RE.match(text.strip().lower())
    if m is None:
        raise DenvError(
            f"malformed tag {text!r}; expected family[:flavor][@version], "
            "e.g. python@3.12, kotlin:android, go:cgo")
    return RawTag(m["family"], m["flavor"] or GENERIC, m["version"])


# --- Spec ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Spec:
    """The declarative intent: exactly these targets for this project.

    The smart constructor is `make_spec`; it enforces the one spec law: a
    recipe key appears at most once, so two versions of one toolchain cannot
    be requested and version conflicts are unrepresentable downstream.
    """

    targets: tuple[Target, ...]  # sorted, unique keys
    project: Path                # resolved project root


def make_spec(targets: list[Target], project: Path) -> Spec:
    by_key: dict[RecipeKey, Target] = {}
    for t in targets:
        prior = by_key.get(t.key)
        if prior is not None and prior != t:
            raise DenvError(f"conflicting tags {prior} and {t}: "
                            "one toolchain, one version")
        by_key.setdefault(t.key, t)
    if not by_key:
        raise DenvError("no targets given; pass at least one tag, e.g. python")
    ordered = tuple(sorted(by_key.values(), key=str))
    return Spec(ordered, project)


def find_project(start: Path) -> Path:
    """Nearest ancestor holding .git, else `start` itself. Pure directory
    walking: a bare host has no git binary to ask."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


# --- Layout -------------------------------------------------------------------
#
# One name per path, derived once from the root, so no step invents its own
# spelling. Everything mutable lives under `root`; the project checkout is
# never written except for generated, ignored files a build tool demands.


@dataclass(frozen=True, slots=True)
class Layout:
    root: Path

    @property
    def downloads(self) -> Path: return self.root / "downloads"
    @property
    def mamba_bin(self) -> Path: return self.root / "micromamba" / "bin" / "micromamba"
    @property
    def mamba_root(self) -> Path: return self.root / "micromamba" / "root"
    @property
    def conda_host(self) -> Path: return self.root / "conda" / "host"
    def conda_foreign(self, platform: CondaPlatform) -> Path:
        return self.root / "conda" / platform.value
    @property
    def jvm(self) -> Path:
        # conda-forge's openjdk nests the JDK here; the prefix itself is not
        # a JAVA_HOME, only symlinks land in bin.
        return self.conda_host / "lib" / "jvm"
    @property
    def uv_python(self) -> Path: return self.root / "uv" / "python"
    @property
    def venv(self) -> Path: return self.root / "uv" / "venv"
    @property
    def tools(self) -> Path: return self.root / "tools"
    @property
    def android_sdk(self) -> Path: return self.root / "android-sdk"
    @property
    def gradle_home(self) -> Path: return self.root / "gradle-home"
    @property
    def home(self) -> Path: return self.root / "home"
    @property
    def tmp(self) -> Path: return self.root / "tmp"
    @property
    def cache(self) -> Path: return self.root / "cache"
    @property
    def shims(self) -> Path: return self.root / "shims"
    @property
    def activate_sh(self) -> Path: return self.root / "activate.sh"
    @property
    def activate_ps1(self) -> Path: return self.root / "activate.ps1"
    @property
    def manifest(self) -> Path: return self.root / "manifest.json"


def default_root(project: Path, host: Host) -> Path:
    """Per-project, per-user root under the system temp base: ephemeral by
    design, collision-free by hashing the project's absolute path."""
    if override := os.environ.get("DENV_ROOT"):
        return Path(override)
    digest = hashlib.sha256(str(project.resolve()).encode()).hexdigest()[:8]
    slug = re.sub(r"[^a-z0-9]+", "-", project.name.lower()).strip("-") or "project"
    user = f"-{os.getuid()}" if hasattr(os, "getuid") else ""
    base = os.environ.get("DENV_HOME") or str(
        Path(tempfile.gettempdir()) / f"denv{user}")
    return Path(base) / f"{slug}-{digest}"


# --- Env deltas ---------------------------------------------------------------
#
# The environment an activation script exports is a value, composed from
# per-recipe deltas by a lawful merge, then rendered twice (sh, ps1) and used
# a third time directly for verification probes. One source of truth.


@dataclass(frozen=True, slots=True)
class EnvDelta:
    vars: tuple[tuple[str, str], ...] = ()   # name -> literal value
    path: tuple[Path, ...] = ()              # PATH prepends, significant order
    unset: frozenset[str] = frozenset()

    def __add__(self, other: "EnvDelta") -> "EnvDelta":
        return merge_deltas([self, other])


def merge_deltas(deltas: list[EnvDelta]) -> EnvDelta:
    """Monoid with conflict detection: two recipes may agree on a variable,
    never disagree. Path entries keep first-occurrence order; sets union."""
    vars_: dict[str, str] = {}
    path: list[Path] = []
    unset: set[str] = set()
    for delta in deltas:
        for name, value in delta.vars:
            if vars_.get(name, value) != value:
                raise DenvError(
                    f"recipes disagree on ${name}: "
                    f"{vars_[name]!r} vs {value!r}")
            vars_[name] = value
        for entry in delta.path:
            if entry not in path:
                path.append(entry)
        unset |= delta.unset
    return EnvDelta(tuple(sorted(vars_.items())), tuple(path), frozenset(unset))
