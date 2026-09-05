"""One executor per step variant, and the total dispatch over them.

Every executor is idempotent: it checks its own postcondition and returns
without work when the step is already satisfied. That is what makes
re-running provision the repair action rather than a reinstall."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import zipfile
from pathlib import Path, PurePosixPath
from typing import assert_never

from btm_setup_env.catalog import GOOGLE_MAVEN, conda_bin_dirs, jvm_home
from btm_setup_env.model import (
    OS,
    CondaPlatform,
    DenvError,
    Layout,
)
from btm_setup_env.shell.process import run_logged
from btm_setup_env.shell.root import Ctx
from btm_setup_env.shell.supply import ensure_micromamba, uv_binary
from btm_setup_env.shell.transfer import (
    extract_tar,
    extract_zip,
    fetch,
    log,
    verify_sha256,
)
from btm_setup_env.steps import (
    Aapt2Shim,
    AndroidSdk,
    ArchiveKind,
    BindGradleProject,
    CompilerShims,
    CondaEnv,
    Fetch,
    GhcupToolchain,
    Step,
    UvShim,
    UvVenv,
)

DIGITS_AND_DOT = frozenset("0123456789.")


_COMPILERS = (("cc", ("-gcc", "-clang")), ("c++", ("-g++", "-clang++")))


NUMBERS = re.compile(r"\d+")


def conda_create(ctx: Ctx, step: CondaEnv) -> None:
    prefix = ctx.layout.root / step.prefix_rel
    recorded = ctx.manifest.conda.get(step.prefix_rel)
    if recorded == step.packages and (prefix / "conda-meta").is_dir():
        return
    ensure_micromamba(ctx)
    assert step.platform is not None  # Planner resolves None to host platform.
    log(f"conda {step.prefix_rel} ({step.platform.value}): " + " ".join(step.packages))
    run_logged(
        f"micromamba create {step.prefix_rel}",
        [
            str(ctx.mamba),
            "create",
            "--yes",
            "--quiet",
            "--no-rc",
            "--prefix",
            str(prefix),
            "--platform",
            step.platform.value,
            "--channel",
            "conda-forge",
            *step.packages,
        ],
        ctx.tool_env(),
    )
    ctx.record(conda={**ctx.manifest.conda, step.prefix_rel: step.packages})
    ctx.save_manifest()


def do_uv_venv(ctx: Ctx, step: UvVenv) -> None:
    layout, host = ctx.layout, ctx.host
    python = layout.venv / (
        "Scripts/python.exe" if host.os is OS.WINDOWS else "bin/python"
    )
    if python.exists() and ctx.manifest.uv_python == step.version:
        return
    uv = uv_binary(ctx)
    env = ctx.tool_env(
        UV_PYTHON_INSTALL_DIR=str(layout.uv_python),
        UV_CACHE_DIR=str(layout.cache / "uv"),
        UV_PYTHON_PREFERENCE="only-managed",
    )
    log("installing CPython " + (step.version or "(uv default)"))
    run_logged(
        "uv python install",
        [uv, "python", "install", *([step.version] if step.version else [])],
        env,
    )
    if layout.venv.exists():
        shutil.rmtree(layout.venv)
    run_logged(
        "uv venv",
        [
            uv,
            "venv",
            "--seed",
            *(["--python", step.version] if step.version else []),
            str(layout.venv),
        ],
        env,
    )
    ctx.record(uv_python=step.version)
    ctx.save_manifest()


def do_fetch(ctx: Ctx, step: Fetch) -> None:
    dest = ctx.layout.root / step.dest_rel
    if step.kind is ArchiveKind.BIN and dest.exists():
        return
    archives = (ArchiveKind.ZIP, ArchiveKind.TAR)
    if step.kind in archives and dest.is_dir() and any(dest.iterdir()):
        return
    archive = ctx.layout.downloads / PurePosixPath(step.url).name
    log(f"fetching {step.name}")
    fetch(step.url, archive)
    if step.sha256 is not None:
        verify_sha256(archive, step.sha256)
    else:
        # Never make a trust decision silently: the agent driving this run
        # should know verification was skipped and why.
        log(
            f"{step.name}: fetched WITHOUT digest verification"
            " (no pinned publisher digest for this version)"
        )
    if step.kind is ArchiveKind.BIN:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive, dest)
        dest.chmod(0o755)
        return
    partial = dest.with_name(dest.name + ".partial")
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True)
    extract = extract_zip if step.kind is ArchiveKind.ZIP else extract_tar
    extract(archive, partial, step.strip)
    if dest.exists():
        shutil.rmtree(dest)
    os.replace(partial, dest)


def _jvm_env_vars(ctx: Ctx) -> dict[str, str]:
    home = jvm_home(ctx.layout, ctx.host)
    return {
        "JAVA_HOME": str(home),
        "ANDROID_HOME": str(ctx.layout.android_sdk),
        "ANDROID_SDK_ROOT": str(ctx.layout.android_sdk),
    }


def do_android_sdk(ctx: Ctx, step: AndroidSdk) -> None:
    layout = ctx.layout
    sdk = layout.android_sdk
    packages = [
        "platform-tools",
        f"platforms;android-{step.api}",
        f"build-tools;{step.api}.0.0",
    ]
    wanted = [
        sdk / "platform-tools",
        sdk / "platforms" / f"android-{step.api}",
        sdk / "build-tools" / f"{step.api}.0.0",
    ]
    if all(p.is_dir() for p in wanted):
        return
    suffix = ".bat" if ctx.host.os is OS.WINDOWS else ""
    sdkmanager = sdk / "cmdline-tools" / "latest" / "bin" / f"sdkmanager{suffix}"
    if not sdkmanager.exists():
        raise DenvError(f"sdkmanager missing at {sdkmanager}")
    env = ctx.tool_env(**_jvm_env_vars(ctx))
    subprocess.run(
        [str(sdkmanager), "--licenses"],
        env=env,
        input="y\n" * 60,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,  # The install reports license refusal.
        timeout=600,
    )
    log("installing SDK packages: " + " ".join(packages))
    run_logged("sdkmanager --install", [str(sdkmanager), "--install", *packages], env)


def do_ghcup(ctx: Ctx, step: GhcupToolchain) -> None:
    layout = ctx.layout
    base = layout.tools / "haskell"
    ghc = base / ".ghcup" / "bin" / "ghc"
    cabal = base / ".ghcup" / "bin" / "cabal"
    if ghc.exists() and cabal.exists():
        return
    path = os.pathsep.join(
        [
            str(base / "bin"),
            str(layout.shims),
            *map(str, conda_bin_dirs(layout, ctx.host)),
            "/usr/bin",
            "/bin",
        ]
    )
    env = ctx.tool_env(
        GHCUP_INSTALL_BASE_PREFIX=str(base),
        PATH=path,
        CC=str(layout.shims / "cc"),
        LD_LIBRARY_PATH=str(layout.conda_host / "lib"),
    )
    ghcup = str(base / "bin" / "ghcup")
    log(f"ghcup: installing ghc {step.ghc} + cabal (this is a large download)")
    # ghcup refuses reinstall; guard each install for interrupted runs.
    if not ghc.exists():
        run_logged(
            "ghcup install ghc", [ghcup, "install", "ghc", step.ghc, "--set"], env
        )
    if not cabal.exists():
        run_logged(
            "ghcup install cabal",
            [ghcup, "install", "cabal", "recommended", "--set"],
            env,
        )


def do_compiler_shims(ctx: Ctx, step: CompilerShims) -> None:
    """conda compilers carry triple-prefixed names; fixed-name shims give
    CC/CXX a plan-time value and let configure scripts find them."""
    bin_dir = ctx.layout.conda_host / "bin"
    ctx.layout.shims.mkdir(parents=True, exist_ok=True)
    # One directory listing serves every compiler; conda bins hold thousands.
    names = (
        sorted(entry.name for entry in bin_dir.iterdir()) if bin_dir.is_dir() else []
    )
    for shim_name, suffixes in _COMPILERS:
        real = next(
            (
                bin_dir / name
                for suffix in suffixes
                for name in names
                if name.endswith(suffix)
            ),
            None,
        )
        if real is None:
            continue  # c-compiler has no c++.
        for alias in (shim_name, real.name.rsplit("-", 1)[-1]):
            link = ctx.layout.shims / alias
            link.unlink(missing_ok=True)
            link.symlink_to(real)


def do_uv_shim(ctx: Ctx, step: UvShim) -> None:
    """The activated PATH drops the caller's PATH, so uv must live inside."""
    ctx.layout.shims.mkdir(parents=True, exist_ok=True)
    for name in ("uv", "uvx"):
        found = shutil.which(name)
        if found is None:
            continue
        link = ctx.layout.shims / Path(found).name
        link.unlink(missing_ok=True)
        if ctx.host.os is OS.WINDOWS:
            shutil.copy2(found, link)
        else:
            link.symlink_to(found)


def _agp_version(project: Path) -> str | None:
    catalog = project / "gradle" / "libs.versions.toml"
    try:
        text = catalog.read_text()
    except OSError:
        return None
    return _toml_string(text, "agp")


def _toml_string(text: str, key: str) -> str | None:
    """The quoted value of a top-level `key = "..."` line; one pass over lines."""
    for line in text.split("\n"):
        head, sep, value = line.partition("=")
        if sep and head.strip() == key:
            value = value.lstrip()
            close = value.find('"', 1) if value.startswith('"') else -1
            return value[1:close] if close > 1 else None
    return None


def _tag_contents(text: str, tag: str) -> list[str]:
    """Contents of every `<tag>...</tag>` span, non-empty; one pass."""
    opener, closer = f"<{tag}>", f"</{tag}>"
    found: list[str] = []
    position = 0
    while (start := text.find(opener, position)) != -1:
        end = text.find(closer, start + len(opener))
        if end == -1:
            break
        if end > start + len(opener):
            found.append(text[start + len(opener) : end])
        position = end + len(closer)
    return found


def _aapt2_rank(version: str) -> tuple[int, tuple[int, ...]]:
    """Newest last: a stable release outranks a qualifier, then the numbers in
    order. Google lists ascending today; this does not rely on it."""
    return (
        int(_stable_aapt2(version)),
        tuple(int(found) for found in NUMBERS.findall(version)),
    )


def _stable_aapt2(version: str) -> bool:
    """`<digits and dots>-<digits>`: a released build, no qualifier."""
    head, dash, build = version.partition("-")
    return (
        bool(dash)
        and bool(head)
        and set(head) <= DIGITS_AND_DOT
        and build.isascii()
        and build.isdigit()
    )


def _aapt2_version(ctx: Ctx) -> str:
    """The aapt2 AGP itself would resolve: derived from the project's pinned
    AGP when one exists, else the newest stable, so nothing here goes stale."""
    metadata = ctx.layout.downloads / "aapt2-maven-metadata.xml"
    metadata.unlink(missing_ok=True)
    fetch(f"{GOOGLE_MAVEN}/com/android/tools/build/aapt2/maven-metadata.xml", metadata)
    versions = _tag_contents(metadata.read_text(), "version")
    agp = _agp_version(Path(ctx.manifest.project or "."))
    matching = [v for v in versions if v.startswith(f"{agp}-")] if agp else []
    if agp and not matching:
        raise DenvError(f"Google publishes no aapt2 for AGP {agp}")
    usable = matching or [v for v in versions if _stable_aapt2(v)]
    if not usable:
        raise DenvError("no usable aapt2 version in Google's maven metadata")
    return max(usable, key=_aapt2_rank)


def do_aapt2_shim(ctx: Ctx, step: Aapt2Shim) -> None:
    layout = ctx.layout
    real = layout.root / "aapt2" / "aapt2.x86_64"
    if not real.exists():
        version = _aapt2_version(ctx)
        log(f"installing aapt2 {version} (emulated)")
        jar = layout.downloads / f"aapt2-{version}-linux.jar"
        fetch(
            f"{GOOGLE_MAVEN}/com/android/tools/build/aapt2/{version}/"
            f"aapt2-{version}-linux.jar",
            jar,
        )
        real.parent.mkdir(parents=True, exist_ok=True)
        with (
            zipfile.ZipFile(jar) as zf,
            zf.open("aapt2") as src,
            open(real, "wb") as out,
        ):
            shutil.copyfileobj(src, out)
        real.chmod(0o755)
    write_qemu_wrapper(
        ctx, step.qemu_binary, step.sysroot_platform, real, layout.shims / "aapt2"
    )
    _set_gradle_property(
        layout, "android.aapt2FromMavenOverride", str(layout.shims / "aapt2")
    )


def write_qemu_wrapper(
    ctx: Ctx, qemu_binary: str, platform: CondaPlatform, real: Path, wrapper: Path
) -> None:
    """One executable, emulated transparently. The wrapper must write nothing
    to stdout: callers like AGP speak a daemon protocol over these pipes."""
    layout = ctx.layout
    foreign = layout.conda_foreign(platform)
    triple = (
        "x86_64-conda-linux-gnu"
        if platform is CondaPlatform.LINUX_64
        else "aarch64-conda-linux-gnu"
    )
    sysroot = foreign / triple / "sysroot"
    # The loader expects libgcc in sysroot/lib64, but conda stores it in prefix/lib.
    lib64 = sysroot / "lib64"
    libgcc = foreign / "lib" / "libgcc_s.so.1"
    if libgcc.exists() and not (lib64 / "libgcc_s.so.1").exists():
        lib64.mkdir(parents=True, exist_ok=True)
        shutil.copy2(libgcc, lib64 / "libgcc_s.so.1")
    qemu = layout.conda_host / "bin" / qemu_binary
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "#!/bin/sh\n"
        "# Generated by btm-setup-env. exec keeps fds and exit status intact;\n"
        "# nothing may be written to stdout.\n"
        f"exec {shlex.quote(str(qemu))} -L {shlex.quote(str(sysroot))} "
        f'{shlex.quote(str(real))} "$@"\n'
    )
    partial = wrapper.with_name(wrapper.name + ".partial")
    partial.write_text(text)
    partial.chmod(0o755)
    os.replace(partial, wrapper)


def _set_gradle_property(layout: Layout, key: str, value: str) -> None:
    properties = layout.gradle_home / "gradle.properties"
    properties.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if properties.exists():
        lines = [
            line
            for line in properties.read_text().splitlines()
            if not line.startswith(f"{key}=")
        ]
    lines.append(f"{key}={value}")
    properties.write_text("\n".join(lines) + "\n")


def do_bind_gradle(ctx: Ctx, step: BindGradleProject) -> None:
    """local.properties overrides the SDK env vars, so a stale one is the
    first thing to mislead a build; rewrite its sdk.dir on every run while
    preserving any other keys the project put there."""
    project = Path(ctx.manifest.project or ".")
    gradle_markers = (
        "settings.gradle",
        "settings.gradle.kts",
        "build.gradle",
        "build.gradle.kts",
    )
    if not any((project / marker).exists() for marker in gradle_markers):
        return
    local = project / "local.properties"
    lines = []
    if local.exists():
        lines = [
            line
            for line in local.read_text().splitlines()
            if not line.startswith("sdk.dir=")
        ]
    lines.append(f"sdk.dir={ctx.layout.android_sdk}")
    local.write_text("\n".join(lines) + "\n")


def execute(ctx: Ctx, step: Step) -> None:
    """Exhaustive over the closed sum, so a new variant is a type error here
    rather than a KeyError partway through a provision."""
    match step:
        case CondaEnv():
            conda_create(ctx, step)
        case UvVenv():
            do_uv_venv(ctx, step)
        case Fetch():
            do_fetch(ctx, step)
        case GhcupToolchain():
            do_ghcup(ctx, step)
        case AndroidSdk():
            do_android_sdk(ctx, step)
        case Aapt2Shim():
            do_aapt2_shim(ctx, step)
        case CompilerShims():
            do_compiler_shims(ctx, step)
        case UvShim():
            do_uv_shim(ctx, step)
        case BindGradleProject():
            do_bind_gradle(ctx, step)
        case _:
            assert_never(step)
