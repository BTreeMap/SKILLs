"""The imperative shell: downloads, extraction, micromamba, step executors.

Idempotence is the governing law: every executor checks a postcondition and
skips completed work, so re-running provision is the repair action, and an
interrupted run never leaves state a later run would trust. Downloads land
under a temporary name and rename on success for the same reason.

Provisioning-time subprocesses inherit the caller's environment with HOME,
TMPDIR, and TLS roots redirected; only the *activation* environment is fully
hermetic. certifi supplies the CA bundle so everything works on images that
ship no system roots.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import ssl
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import certifi

from .catalog import GOOGLE_MAVEN, conda_bin_dirs, jvm_home, qemu_steps
from .model import (
    OS,
    CondaPlatform,
    DenvError,
    Host,
    Layout,
    QemuUser,
    Unsupported,
    emulation,
)
from .plan import Plan
from .render import realize, render_ps1, render_sh
from .steps import (
    Aapt2Shim,
    AndroidSdk,
    BindGradleProject,
    CompilerShims,
    CondaEnv,
    Fetch,
    GhcupToolchain,
    UvShim,
    UvVenv,
)

MICROMAMBA_VERSION = "2.9.0-0"
MICROMAMBA_RELEASES = (
    "https://github.com/mamba-org/micromamba-releases/releases/download"
)

_SSL = ssl.create_default_context(cafile=certifi.where())


def log(message: str) -> None:
    print(f"envctl: {message}", file=sys.stderr)


# --- Downloads and extraction -------------------------------------------------


def fetch(url: str, target: Path) -> None:
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": "envctl"})
    with (
        urllib.request.urlopen(request, context=_SSL) as src,
        open(partial, "wb") as out,
    ):
        shutil.copyfileobj(src, out)
    os.replace(partial, target)


def verify_sha256(path: Path, expected: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise DenvError(
            f"digest mismatch for {path.name}\n"
            f"  expected {expected}\n  actual   {actual}"
        )


def _stripped(name: str, strip: int) -> tuple[str, ...] | None:
    parts = PurePosixPath(name).parts[strip:]
    if not parts or ".." in parts or parts[0].startswith("/"):
        return None
    return parts


def _extract_zip(archive: Path, dest: Path, strip: int) -> None:
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            parts = _stripped(info.filename, strip)
            if parts is None or info.is_dir():
                continue
            target = dest.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = (info.external_attr >> 16) & 0o170777
            if stat.S_ISLNK(mode):
                target.symlink_to(zf.read(info).decode())
                continue
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            if mode & 0o777:
                os.chmod(target, mode & 0o777)


def _extract_tar(archive: Path, dest: Path, strip: int) -> None:
    with tarfile.open(archive) as tf:
        members = []
        for member in tf.getmembers():
            parts = _stripped(member.name, strip)
            if parts is None:
                continue
            member.name = str(PurePosixPath(*parts))
            members.append(member)
        try:
            tf.extractall(dest, members=members, filter="tar")
        except TypeError:  # pre-3.11.4: no filter parameter
            tf.extractall(dest, members=members)


def run_logged(
    what: str, cmd: list[str], env: dict[str, str], stdin_text: str | None = None
) -> None:
    """Run quietly; on failure surface the tail, which is where build tools
    put the sentence worth reading."""
    result = subprocess.run(
        cmd,
        env=env,
        input=stdin_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,  # the tail below is a better error than CalledProcessError
    )
    if result.returncode != 0:
        tail = "\n".join((result.stdout or "").splitlines()[-40:])
        raise DenvError(f"{what} failed (exit {result.returncode}):\n{tail}")


# --- Context ------------------------------------------------------------------


@dataclass
class Ctx:
    layout: Layout
    host: Host
    manifest: dict = field(default_factory=dict)

    @property
    def mamba(self) -> Path:
        name = "micromamba.exe" if self.host.os is OS.WINDOWS else "micromamba"
        return self.layout.mamba_bin.with_name(name)

    def tool_env(self, **extra: str) -> dict[str, str]:
        env = dict(os.environ)
        env.update(
            HOME=str(self.layout.home),
            TMPDIR=str(self.layout.tmp),
            SSL_CERT_FILE=certifi.where(),
            MAMBA_ROOT_PREFIX=str(self.layout.mamba_root),
        )
        env.update(extra)
        return env

    def save_manifest(self) -> None:
        path = self.layout.manifest
        partial = path.with_name(path.name + ".partial")
        partial.write_text(json.dumps(self.manifest, indent=2, sort_keys=True))
        os.replace(partial, path)


def load_manifest(layout: Layout) -> dict:
    try:
        return json.loads(layout.manifest.read_text())
    except (OSError, ValueError):
        return {}


# --- micromamba ---------------------------------------------------------------


def ensure_micromamba(ctx: Ctx) -> None:
    if ctx.mamba.exists():
        return
    platform = ctx.host.conda_platform.value
    log(f"installing micromamba {MICROMAMBA_VERSION} ({platform})")
    url = f"{MICROMAMBA_RELEASES}/{MICROMAMBA_VERSION}/micromamba-{platform}"
    archive = ctx.layout.downloads / f"micromamba-{platform}"
    fetch(url, archive)
    # The publisher ships a digest beside each binary; fetching it keeps the
    # check architecture-independent with no table of constants here.
    fetch(url + ".sha256", archive.with_name(archive.name + ".sha256"))
    expected = archive.with_name(archive.name + ".sha256").read_text().split()[0]
    verify_sha256(archive, expected)
    ctx.mamba.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, ctx.mamba)
    ctx.mamba.chmod(0o755)


def conda_create(ctx: Ctx, step: CondaEnv) -> None:
    prefix = ctx.layout.root / step.prefix_rel
    recorded = ctx.manifest.setdefault("conda", {}).get(step.prefix_rel)
    if recorded == list(step.packages) and (prefix / "conda-meta").is_dir():
        return
    ensure_micromamba(ctx)
    assert step.platform is not None  # planner resolved None to the host's
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
    ctx.manifest["conda"][step.prefix_rel] = list(step.packages)
    ctx.save_manifest()


# --- Step executors -----------------------------------------------------------


def _uv(ctx: Ctx) -> str:
    found = shutil.which("uv")
    if found is None:
        raise DenvError(
            "uv is required and was not found on PATH; see https://docs.astral.sh/uv/"
        )
    return found


def do_uv_venv(ctx: Ctx, step: UvVenv) -> None:
    layout, host = ctx.layout, ctx.host
    python = layout.venv / (
        "Scripts/python.exe" if host.os is OS.WINDOWS else "bin/python"
    )
    if python.exists() and ctx.manifest.get("uv_python") == step.version:
        return
    uv = _uv(ctx)
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
    ctx.manifest["uv_python"] = step.version
    ctx.save_manifest()


def do_fetch(ctx: Ctx, step: Fetch) -> None:
    dest = ctx.layout.root / step.dest_rel
    if step.kind == "bin" and dest.exists():
        return
    if step.kind in ("zip", "tar") and dest.is_dir() and any(dest.iterdir()):
        return
    archive = ctx.layout.downloads / PurePosixPath(step.url).name
    log(f"fetching {step.name}")
    fetch(step.url, archive)
    if step.sha256 is not None:
        verify_sha256(archive, step.sha256)
    if step.kind == "bin":
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive, dest)
        dest.chmod(0o755)
        return
    partial = dest.with_name(dest.name + ".partial")
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True)
    (_extract_zip if step.kind == "zip" else _extract_tar)(archive, partial, step.strip)
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
    # Licenses first, so the install has nothing to ask; the install's error
    # is the one worth reporting, so license failures stay silent.
    subprocess.run(
        [str(sdkmanager), "--licenses"],
        env=env,
        input="y\n" * 60,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,  # a licence refusal is reported by the install that follows
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
    # Guarded separately: ghcup refuses to reinstall, so a run interrupted
    # between the two must not repeat the first.
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


_COMPILERS = (("cc", ("-gcc", "-clang")), ("c++", ("-g++", "-clang++")))


def do_compiler_shims(ctx: Ctx, step: CompilerShims) -> None:
    """conda compilers carry triple-prefixed names; fixed-name shims give
    CC/CXX a plan-time value and let configure scripts find them."""
    bin_dir = ctx.layout.conda_host / "bin"
    ctx.layout.shims.mkdir(parents=True, exist_ok=True)
    for shim_name, suffixes in _COMPILERS:
        real = next(
            (
                p
                for suffix in suffixes
                for p in sorted(bin_dir.glob(f"*{suffix}"))
                if p.name.endswith(suffix)
            ),
            None,
        )
        if real is None:
            continue  # recipe without this half (c-compiler has no c++)
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


# --- aapt2: Google ships linux aapt2 as x86_64 only ---------------------------


def _agp_version(project: Path) -> str | None:
    catalog = project / "gradle" / "libs.versions.toml"
    try:
        text = catalog.read_text()
    except OSError:
        return None
    m = re.search(r'^agp\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else None


def _aapt2_version(ctx: Ctx) -> str:
    """The aapt2 AGP itself would resolve: derived from the project's pinned
    AGP when one exists, else the newest stable, so nothing here goes stale."""
    metadata = ctx.layout.downloads / "aapt2-maven-metadata.xml"
    metadata.unlink(missing_ok=True)
    fetch(f"{GOOGLE_MAVEN}/com/android/tools/build/aapt2/maven-metadata.xml", metadata)
    versions = re.findall(r"<version>([^<]+)</version>", metadata.read_text())
    agp = _agp_version(Path(ctx.manifest.get("project", ".")))
    matching = [v for v in versions if v.startswith(f"{agp}-")] if agp else []
    if agp and not matching:
        raise DenvError(f"Google publishes no aapt2 for AGP {agp}")
    stable = [v for v in versions if re.fullmatch(r"[\d.]+-\d+", v)]
    chosen = (matching or stable)[-1:]
    if not chosen:
        raise DenvError("no usable aapt2 version in Google's maven metadata")
    return chosen[0]


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
    # libgcc lands in the prefix's lib rather than inside the sysroot, and
    # dynamically linked tools name it directly, so place it where the
    # emulated loader looks.
    lib64 = sysroot / "lib64"
    libgcc = foreign / "lib" / "libgcc_s.so.1"
    if libgcc.exists() and not (lib64 / "libgcc_s.so.1").exists():
        lib64.mkdir(parents=True, exist_ok=True)
        shutil.copy2(libgcc, lib64 / "libgcc_s.so.1")
    qemu = layout.conda_host / "bin" / qemu_binary
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "#!/bin/sh\n"
        "# Generated by envctl. exec keeps fds and exit status intact;\n"
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
    project = Path(ctx.manifest.get("project", "."))
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


# --- Orchestration ------------------------------------------------------------


_EXECUTORS = {
    CondaEnv: conda_create,
    UvVenv: do_uv_venv,
    Fetch: do_fetch,
    GhcupToolchain: do_ghcup,
    AndroidSdk: do_android_sdk,
    Aapt2Shim: do_aapt2_shim,
    CompilerShims: do_compiler_shims,
    UvShim: do_uv_shim,
    BindGradleProject: do_bind_gradle,
}


@dataclass(frozen=True, slots=True)
class ProbeResult:
    command: tuple[str, ...]
    ok: bool
    output: str


def provision(plan: Plan) -> list[ProbeResult]:
    layout = plan.layout
    for directory in (
        layout.root,
        layout.downloads,
        layout.home,
        layout.tmp,
        layout.cache,
        layout.shims,
        layout.tmp,
        layout.home / ".config",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(layout, plan.host, load_manifest(layout))
    ctx.manifest["project"] = str(plan.spec.project)
    ctx.manifest["spec"] = [str(t) for t in plan.spec.targets]
    ctx.manifest["host"] = str(plan.host)
    for step in plan.steps:
        _EXECUTORS[type(step)](ctx, step)
    write_activation(plan)
    ctx.save_manifest()
    return verify(plan)


def write_activation(plan: Plan) -> None:
    layout = plan.layout
    for path, text in (
        (layout.activate_sh, render_sh(plan.env, plan.host)),
        (layout.activate_ps1, render_ps1(plan.env, plan.host)),
    ):
        partial = path.with_name(path.name + ".partial")
        partial.write_text(text)
        partial.chmod(0o755)
        os.replace(partial, path)


def verify(plan: Plan) -> list[ProbeResult]:
    """Run every recipe's probes inside the realized activation environment:
    what these prove is exactly what a sourced activate.sh grants."""
    env = realize(plan.env, plan.host)
    results = []
    for command in plan.probes:
        argv0 = shutil.which(command[0], path=env.get("PATH"))
        if argv0 is None:
            results.append(ProbeResult(command, False, "not found on PATH"))
            continue
        try:
            proc = subprocess.run(
                [argv0, *command[1:]],
                env=env,
                timeout=600,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,  # a failing probe is a reported result, not a raise
            )
        except subprocess.TimeoutExpired:
            results.append(ProbeResult(command, False, "probe timed out"))
            continue
        first = next(
            (line for line in (proc.stdout or "").splitlines() if line.strip()), ""
        )
        results.append(ProbeResult(command, proc.returncode == 0, first))
    return results


# --- Standalone foreign-binary shims ------------------------------------------


def make_shim(
    layout: Layout, host: Host, binary: Path, platform: CondaPlatform
) -> Path:
    """Wrap an arbitrary foreign-architecture binary so it runs on this host:
    the aapt2 answer, offered for any binary a build unexpectedly needs."""
    emu = emulation(host, platform)
    match emu:
        case Unsupported(reason=reason):
            raise DenvError(reason)
        case QemuUser():
            pass
        case _:
            raise DenvError(
                f"{platform.value} binaries already run natively "
                f"on {host}; no shim needed"
            )
    if not binary.is_file():
        raise DenvError(f"no such binary: {binary}")
    ctx = Ctx(layout, host, load_manifest(layout))
    host_step, foreign_step = qemu_steps(emu)
    # The host prefix may already exist: merge, because a second create call
    # would replace it and silently discard every earlier package.
    existing = set(ctx.manifest.get("conda", {}).get("conda/host", []))
    merged = tuple(sorted(existing | set(host_step.packages)))
    conda_create(ctx, CondaEnv("conda/host", host.conda_platform, merged))
    conda_create(ctx, foreign_step)
    wrapper = layout.shims / binary.name
    write_qemu_wrapper(ctx, emu.qemu_binary, platform, binary.resolve(), wrapper)
    ctx.save_manifest()
    return wrapper
