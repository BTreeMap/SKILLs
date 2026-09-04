"""The closed (family, flavor) -> recipe table.

A recipe answers three questions, each as pure data or a pure function:
which steps materialize the toolchain on a given host, which environment
delta activates it, and which probe commands prove it works. The catalog is
the only module that knows suppliers and URLs; extending the skill to a new
language means adding one entry here and nothing anywhere else.

Suppliers, each the only sensible one for what it provides:
  uv           CPython interpreters and venvs (the skill is all-in on uv)
  conda-forge  everything it packages well, via micromamba, one channel
  publisher    what only the publisher ships: Android SDK + aapt2 (Google),
               ghcup (haskell.org), kotlin-native prebuilts (JetBrains)
  the project  pinned wrappers (gradlew, package.json, Cargo.toml): never
               reinstalled here; a second copy on PATH only confuses builds
"""

from __future__ import annotations

import difflib
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from .model import (
    GENERIC,
    OS,
    Arch,
    CondaPlatform,
    DenvError,
    EnvDelta,
    Host,
    Layout,
    QemuUser,
    RawTag,
    RecipeKey,
    Target,
    emulation,
)
from .steps import (
    Aapt2Shim,
    AndroidSdk,
    BindGradleProject,
    CompilerShims,
    CondaEnv,
    Fetch,
    GhcupToolchain,
    Step,
    UvShim,
    UvVenv,
)

# --- Pinned publisher inputs ---
#
# Conda packages resolve at install time and @version pins on demand.
# Publisher archives are pinned here with available digests.

ANDROID_TOOLS_REVISION = "13114758"
ANDROID_TOOLS_SHA256 = {
    OS.LINUX: "7ec965280a073311c339e571cd5de778b9975026cfcbe79f2b1cdcb1e15317ee",
    OS.MACOS: "5673201e6f3869f418eeed3b5cb6c4be7401502bd0aae1b12a29d164d647a54e",
    OS.WINDOWS: "98b565cb657b012dae6794cefc0f66ae1efb4690c699b78a614b4a6a3505b003",
}
ANDROID_OS_KEY = {OS.LINUX: "linux", OS.MACOS: "mac", OS.WINDOWS: "win"}
DEFAULT_ANDROID_API = 35

GHCUP_VERSION = "0.1.50.2"
GHCUP_TRIPLE = {
    (OS.LINUX, Arch.X86_64): "x86_64-linux",
    (OS.LINUX, Arch.ARM64): "aarch64-linux",
    (OS.MACOS, Arch.X86_64): "x86_64-apple-darwin",
    (OS.MACOS, Arch.ARM64): "aarch64-apple-darwin",
}
# Publisher digests for exactly GHCUP_VERSION, from
# https://downloads.haskell.org/~ghcup/0.1.50.2/SHA256SUMS. A pinned version
# with an unpinned hash is half a pin.
GHCUP_SHA256 = {
    "x86_64-linux": "ff6288df9758211372d8242fe830d8e6be6a8365d9406f1c9bde144b7e744143",
    "aarch64-linux": "a8f86745eb2381ca19f4ebd17652957c2e404dad8f7bb2bdfd62feab9fcf8ddd",
    "x86_64-apple-darwin": (
        "4ac88180ea1e54670efbb894fdb9190e94af8dce18d837ee37c15b61724d045a"
    ),
    "aarch64-apple-darwin": (
        "660d6570a31b380601eb36e61ccdf7dedb7ab54b889dcac708f92152eddb2a20"
    ),
}

KOTLIN_NATIVE_VERSION = "2.2.20"
KOTLIN_NATIVE_SLUG = {
    CondaPlatform.LINUX_64: ("linux-x86_64", "tar"),
    CondaPlatform.OSX_64: ("macos-x86_64", "tar"),
    CondaPlatform.OSX_ARM64: ("macos-aarch64", "tar"),
    CondaPlatform.WIN_64: ("windows-x86_64", "zip"),
}
# Publisher digests for exactly KOTLIN_NATIVE_VERSION, from the GitHub
# release's .sha256 assets. A user-pinned other version fetches unverified,
# and the fetch executor says so out loud.
KOTLIN_NATIVE_SHA256 = {
    CondaPlatform.LINUX_64: (
        "d857fee2b4e3fd6d2d401a3a9400dc40c20de1d023df652721717d3d199ed0dc"
    ),
    CondaPlatform.OSX_64: (
        "9a6b0142bc74c8aaafbe19c3f0253ea31aa15ac393d51cefcd29e237709e1bb8"
    ),
    CondaPlatform.OSX_ARM64: (
        "5270e5f708ffed15eb11a029b8068b73321fcf496c7103dffa909e49d27125e6"
    ),
    CondaPlatform.WIN_64: (
        "42809169e8779b8a14afbe95c06ea728a3de8e19b7c16ac1eeb9621461eeb1f0"
    ),
}

GOOGLE_MAVEN = "https://dl.google.com/dl/android/maven2"


# --- Pure helpers ---


def conda_spec(package: str, version: str | None) -> str:
    return package if version is None else f"{package}={version}"


def host_conda(*packages: str) -> CondaEnv:
    """Packages for the host-native prefix (platform None: the host's own).
    The planner merges every such step into one create call; recipes never
    worry about the ordering."""
    return CondaEnv("conda/host", None, tuple(sorted(packages)))


def qemu_steps(emu: QemuUser) -> tuple[CondaEnv, CondaEnv]:
    """The two prefixes emulation needs: the emulator beside the host tools,
    and a sysroot of the foreign platform for its dynamic linker. libgcc
    rides along because common tools name it directly."""
    foreign = (
        CondaPlatform.LINUX_64
        if "x86_64" in emu.qemu_package
        else CondaPlatform.LINUX_AARCH64
    )
    return (
        host_conda(emu.qemu_package),
        CondaEnv(
            f"conda/{foreign.value}",
            foreign,
            tuple(sorted((emu.sysroot_package, "libgcc"))),
        ),
    )


def _no_windows(host: Host, what: str) -> None:
    if host.os is OS.WINDOWS:
        raise DenvError(f"{what} is not provisionable on windows; use WSL")


def _venv_bin(layout: Layout, host: Host) -> Path:
    return layout.venv / ("Scripts" if host.os is OS.WINDOWS else "bin")


def conda_bin_dirs(layout: Layout, host: Host) -> tuple[Path, ...]:
    """Where executables land in a conda prefix, per OS."""
    p = layout.conda_host
    if host.os is OS.WINDOWS:
        return (p, p / "Library" / "bin", p / "Scripts", p / "bin")
    return (p / "bin",)


def jvm_home(layout: Layout, host: Host) -> Path:
    # openjdk nests the JDK; the prefix is not JAVA_HOME.
    if host.os is OS.WINDOWS:
        return layout.conda_host / "Library" / "lib" / "jvm"
    return layout.jvm


def _jvm_env(layout: Layout, host: Host) -> EnvDelta:
    return EnvDelta(
        vars=(("JAVA_HOME", str(jvm_home(layout, host))),),
        path=(jvm_home(layout, host) / "bin",),
        unset=frozenset(
            {"JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "KOTLIN_HOME"}
        ),
    )


def _cc_env(layout: Layout, cxx: bool = False) -> EnvDelta:
    vars_ = [("CC", str(layout.shims / "cc"))]
    if cxx:
        vars_.append(("CXX", str(layout.shims / "c++")))
    return EnvDelta(vars=tuple(vars_))


# --- Recipe ---


@dataclass(frozen=True, slots=True)
class Recipe:
    key: RecipeKey
    summary: str
    version_doc: str | None  # @version help text; None means no version
    requirements: Callable[[Host, str | None], tuple[Step, ...]]
    env: Callable[[Layout, Host], EnvDelta]
    probes: tuple[tuple[str, ...], ...]


def _conda_only(tool: str, host: Host, version: str | None) -> tuple[Step, ...]:
    """One conda package and nothing else. Named rather than a lambda with a
    late-binding default, which is both the profile's shape and inferrable."""
    return (host_conda(conda_spec(tool, version)),)


def _recipes() -> dict[RecipeKey, Recipe]:  # noqa: PLR0915
    # This function is the catalog; statement count tracks entries, not branching.
    r: list[Recipe] = []

    # Python
    r.append(
        Recipe(
            ("python", GENERIC),
            "uv-managed CPython + venv",
            "CPython version, e.g. 3.12",
            lambda host, v: (UvVenv(v), UvShim()),
            lambda layout, host: EnvDelta(
                vars=(
                    ("PIP_CACHE_DIR", str(layout.cache / "pip")),
                    ("UV_CACHE_DIR", str(layout.cache / "uv")),
                    ("UV_PYTHON_INSTALL_DIR", str(layout.uv_python)),
                    ("UV_PYTHON_PREFERENCE", "only-managed"),
                    ("VIRTUAL_ENV", str(layout.venv)),
                ),
                path=(_venv_bin(layout, host),),
                unset=frozenset({"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"}),
            ),
            (("python", "--version"),),
        )
    )

    # JavaScript / TypeScript
    def js_env(layout: Layout, host: Host) -> EnvDelta:
        # npm expects lowercase names.
        return EnvDelta(
            vars=(
                ("npm_config_cache", str(layout.cache / "npm")),
                ("npm_config_update_notifier", "false"),
            )
        )

    r.append(
        Recipe(
            ("javascript", GENERIC),
            "nodejs + npm",
            "nodejs version, e.g. 22",
            lambda host, v: (host_conda(conda_spec("nodejs", v)),),
            js_env,
            (("node", "--version"), ("npm", "--version")),
        )
    )
    r.append(
        Recipe(
            ("typescript", GENERIC),
            "nodejs + tsc",
            "typescript version",
            lambda host, v: (host_conda("nodejs", conda_spec("typescript", v)),),
            js_env,
            (("node", "--version"), ("tsc", "--version")),
        )
    )

    # Go
    r.append(
        Recipe(
            ("go", GENERIC),
            "go toolchain",
            "go version, e.g. 1.23",
            lambda host, v: (host_conda(conda_spec("go", v)),),
            lambda layout, host: EnvDelta(
                vars=(
                    ("GOCACHE", str(layout.cache / "go-build")),
                    ("GOPATH", str(layout.cache / "go")),
                    ("GOTOOLCHAIN", "local"),
                )
            ),
            (("go", "version"),),
        )
    )
    r.append(
        Recipe(
            ("go", "cgo"),
            "go + C toolchain for cgo",
            "go version",
            lambda host, v: (
                host_conda(conda_spec("go", v), "c-compiler", "make"),
                CompilerShims(),
            ),
            lambda layout, host: (
                EnvDelta(
                    vars=(
                        ("CGO_ENABLED", "1"),
                        ("GOCACHE", str(layout.cache / "go-build")),
                        ("GOPATH", str(layout.cache / "go")),
                        ("GOTOOLCHAIN", "local"),
                    )
                )
                + _cc_env(layout)
            ),
            (("go", "version"), ("cc", "--version")),
        )
    )

    # Rust
    r.append(
        Recipe(
            ("rust", GENERIC),
            "rust + cargo + linker",
            "rust version",
            lambda host, v: (
                host_conda(conda_spec("rust", v), "c-compiler"),
                CompilerShims(),
            ),
            lambda layout, host: (
                EnvDelta(
                    vars=(
                        ("CARGO_HOME", str(layout.cache / "cargo")),
                        ("RUSTUP_HOME", str(layout.cache / "rustup")),
                    )
                )
                + _cc_env(layout)
            ),
            (("rustc", "--version"), ("cargo", "--version")),
        )
    )

    # C / C++
    def _c_req(host: Host, v: str | None) -> tuple[Step, ...]:
        _no_windows(host, "the C toolchain (conda MSVC needs its own activation)")
        return (host_conda("c-compiler", "make"), CompilerShims())

    def _cpp_req(host: Host, v: str | None) -> tuple[Step, ...]:
        _no_windows(host, "the C++ toolchain (conda MSVC needs its own activation)")
        return (host_conda("cxx-compiler", "make"), CompilerShims())

    r.append(
        Recipe(
            ("c", GENERIC),
            "C compiler + make",
            None,
            _c_req,
            lambda layout, host: _cc_env(layout),
            (("cc", "--version"), ("make", "--version")),
        )
    )
    r.append(
        Recipe(
            ("cpp", GENERIC),
            "C++ compiler + make",
            None,
            _cpp_req,
            lambda layout, host: _cc_env(layout, cxx=True),
            (("c++", "--version"), ("make", "--version")),
        )
    )

    # JVM
    r.append(
        Recipe(
            ("java", GENERIC),
            "JDK",
            "openjdk version, e.g. 21",
            lambda host, v: (host_conda(conda_spec("openjdk", v)),),
            _jvm_env,
            (("javac", "-version"),),
        )
    )
    r.append(
        Recipe(
            ("kotlin", GENERIC),
            "kotlinc + JDK",
            "kotlin version",
            lambda host, v: (host_conda(conda_spec("kotlin", v)),),
            _jvm_env,
            (("kotlinc", "-version"),),
        )
    )
    r.append(
        Recipe(
            ("gradle", GENERIC),
            "standalone gradle; prefer the project's gradlew when one exists",
            "gradle version",
            lambda host, v: (host_conda(conda_spec("gradle", v)),),
            lambda layout, host: (
                _jvm_env(layout, host)
                + EnvDelta(vars=(("GRADLE_USER_HOME", str(layout.gradle_home)),))
            ),
            (("gradle", "--version"),),
        )
    )
    r.append(
        Recipe(
            ("maven", GENERIC),
            "maven + JDK",
            "maven version",
            lambda host, v: (host_conda(conda_spec("maven", v)),),
            _jvm_env,
            (("mvn", "--version"),),
        )
    )

    # Android
    def _android_req(host: Host, v: str | None) -> tuple[Step, ...]:
        api = _parse_api(v)
        url = (
            "https://dl.google.com/android/repository/"
            f"commandlinetools-{ANDROID_OS_KEY[host.os]}-"
            f"{ANDROID_TOOLS_REVISION}_latest.zip"
        )
        steps: list[Step] = [
            host_conda("openjdk"),
            # The archive's top directory becomes .../latest.
            Fetch(
                "android-cmdline-tools",
                url,
                ANDROID_TOOLS_SHA256[host.os],
                "zip",
                "android-sdk/cmdline-tools/latest",
                strip=1,
            ),
            AndroidSdk(api),
            BindGradleProject(),
        ]
        # Linux aapt2 is x86_64-only; add a QEMU shim where needed.
        match emulation(host, CondaPlatform.LINUX_64):
            case QemuUser() as emu if host.os is OS.LINUX:
                steps.extend(qemu_steps(emu))
                steps.append(Aapt2Shim(emu.qemu_binary, CondaPlatform.LINUX_64))
        return tuple(steps)

    def _android_env(layout: Layout, host: Host) -> EnvDelta:
        return _jvm_env(layout, host) + EnvDelta(
            vars=(
                ("ANDROID_HOME", str(layout.android_sdk)),
                ("ANDROID_SDK_ROOT", str(layout.android_sdk)),
                ("GRADLE_USER_HOME", str(layout.gradle_home)),
            ),
            path=(
                layout.android_sdk / "cmdline-tools" / "latest" / "bin",
                layout.android_sdk / "platform-tools",
            ),
        )

    android_probes = (("sdkmanager", "--version"),)
    for family in ("kotlin", "java"):
        r.append(
            Recipe(
                (family, "android"),
                "JDK + Android SDK; gradle and kotlin come from the project's "
                "pinned wrapper and plugins, never from here",
                f"Android API level (default {DEFAULT_ANDROID_API})",
                _android_req,
                _android_env,
                android_probes,
            )
        )

    # Kotlin/Native
    def _konan_req(host: Host, v: str | None) -> tuple[Step, ...]:
        slug = KOTLIN_NATIVE_SLUG.get(host.conda_platform)
        if slug is None:
            raise DenvError(
                f"kotlin:native has no JetBrains prebuilt for {host}; "
                "supported: linux-64, osx-64, osx-arm64, win-64"
            )
        name, kind = slug
        version = v or KOTLIN_NATIVE_VERSION
        ext = "tar.gz" if kind == "tar" else "zip"
        url = (
            "https://github.com/JetBrains/kotlin/releases/download/"
            f"v{version}/kotlin-native-prebuilt-{name}-{version}.{ext}"
        )
        digest = (
            KOTLIN_NATIVE_SHA256[host.conda_platform]
            if version == KOTLIN_NATIVE_VERSION
            else None
        )
        return (
            host_conda("openjdk"),
            Fetch("kotlin-native", url, digest, kind, "tools/kotlin-native", strip=1),
        )

    r.append(
        Recipe(
            ("kotlin", "native"),
            "Kotlin/Native prebuilt + JDK",
            f"kotlin version (default {KOTLIN_NATIVE_VERSION})",
            _konan_req,
            lambda layout, host: (
                _jvm_env(layout, host)
                + EnvDelta(
                    vars=(("KONAN_DATA_DIR", str(layout.cache / "konan")),),
                    path=(layout.tools / "kotlin-native" / "bin",),
                )
            ),
            (("kotlinc-native", "-version"),),
        )
    )

    # C#
    def _dotnet_root(layout: Layout, host: Host) -> Path:
        # conda ships no bin wrapper; set DOTNET_ROOT here.
        base = (
            layout.conda_host / "Library"
            if host.os is OS.WINDOWS
            else layout.conda_host
        )
        return base / "lib" / "dotnet"

    r.append(
        Recipe(
            ("csharp", GENERIC),
            ".NET SDK",
            "dotnet version, e.g. 9",
            lambda host, v: (host_conda(conda_spec("dotnet", v)),),
            lambda layout, host: EnvDelta(
                vars=(
                    ("DOTNET_CLI_HOME", str(layout.home)),
                    ("DOTNET_CLI_TELEMETRY_OPTOUT", "1"),
                    ("DOTNET_NOLOGO", "1"),
                    ("DOTNET_ROOT", str(_dotnet_root(layout, host))),
                    ("NUGET_PACKAGES", str(layout.cache / "nuget")),
                ),
                path=(_dotnet_root(layout, host),),
            ),
            (("dotnet", "--version"),),
        )
    )

    # Haskell
    def _hs_req(host: Host, v: str | None) -> tuple[Step, ...]:
        triple = GHCUP_TRIPLE.get((host.os, host.arch))
        if triple is None:
            raise DenvError(
                "haskell via ghcup is not provisionable on windows; use WSL"
            )
        url = (
            f"https://downloads.haskell.org/~ghcup/{GHCUP_VERSION}/"
            f"{triple}-ghcup-{GHCUP_VERSION}"
        )
        # ghcup needs curl; bindists need tar, xz, C, make, gmp, and ncurses.
        # Keep all dependencies inside the prefix.
        return (
            host_conda("curl", "gmp", "ncurses", "c-compiler", "make", "tar", "xz"),
            Fetch("ghcup", url, GHCUP_SHA256[triple], "bin", "tools/haskell/bin/ghcup"),
            GhcupToolchain(ghc=v or "recommended"),
            CompilerShims(),
        )

    r.append(
        Recipe(
            ("haskell", GENERIC),
            "ghc + cabal via ghcup (best effort)",
            "ghc version (default: ghcup's recommended)",
            _hs_req,
            lambda layout, host: (
                _cc_env(layout)
                + EnvDelta(
                    vars=(
                        ("CABAL_DIR", str(layout.cache / "cabal")),
                        ("GHCUP_INSTALL_BASE_PREFIX", str(layout.tools / "haskell")),
                        ("STACK_ROOT", str(layout.cache / "stack")),
                        # Haskell runtime deps live in conda; only Haskell needs them.
                        ("LD_LIBRARY_PATH", str(layout.conda_host / "lib")),
                    ),
                    path=(
                        layout.tools / "haskell" / ".ghcup" / "bin",
                        layout.tools / "haskell" / "bin",
                    ),
                )
            ),
            (("ghc", "--version"), ("cabal", "--version")),
        )
    )

    # Bash
    def _bash_req(host: Host, v: str | None) -> tuple[Step, ...]:
        _no_windows(host, "the bash toolchain")
        return (host_conda(conda_spec("bash", v), "shellcheck", "go-shfmt"),)

    r.append(
        Recipe(
            ("bash", GENERIC),
            "bash + shellcheck + shfmt",
            "bash version",
            _bash_req,
            lambda layout, host: EnvDelta(),
            (
                ("bash", "--version"),
                ("shellcheck", "--version"),
                ("shfmt", "--version"),
            ),
        )
    )

    # Standalone build tools
    for tool, probe in (
        ("cmake", ("cmake", "--version")),
        ("ninja", ("ninja", "--version")),
    ):
        r.append(
            Recipe(
                (tool, GENERIC),
                tool,
                f"{tool} version",
                partial(_conda_only, tool),
                lambda layout, host: EnvDelta(),
                (probe,),
            )
        )

    return {recipe.key: recipe for recipe in r}


def _parse_api(v: str | None) -> int:
    if v is None:
        return DEFAULT_ANDROID_API
    if not v.isdigit():
        raise DenvError(f"android takes an API level as its version, got {v!r}")
    return int(v)


CATALOG: dict[RecipeKey, Recipe] = _recipes()

# Normalize aliases before lookup; bare "android" maps to java:android.
_ALIAS = {
    "js": "javascript",
    "node": "javascript",
    "ts": "typescript",
    "py": "python",
    "golang": "go",
    "c++": "cpp",
    "cs": "csharp",
    "dotnet": "csharp",
    "sh": "bash",
    "shell": "bash",
}


def resolve_tag(raw: RawTag) -> Target:
    family = _ALIAS.get(raw.family, raw.family)
    key: RecipeKey = (family, raw.flavor)
    if family == "android" and raw.flavor == GENERIC:
        key = ("java", "android")
    recipe = CATALOG.get(key)
    if recipe is None:
        known = sorted(f if fl == GENERIC else f"{f}:{fl}" for f, fl in CATALOG)
        asked = raw.family if raw.flavor == GENERIC else f"{raw.family}:{raw.flavor}"
        hints = difflib.get_close_matches(asked, known, n=3)
        hint = f"; did you mean {', '.join(hints)}?" if hints else ""
        raise DenvError(
            f"unknown target {asked!r}{hint}\nknown targets: {', '.join(known)}"
        )
    if raw.version is not None and recipe.version_doc is None:
        raise DenvError(f"{family} does not take a version")
    return Target(key, raw.version)
