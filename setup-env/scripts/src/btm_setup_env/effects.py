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
import shlex
import shutil
import ssl
import stat
import subprocess
import sys
import tarfile
import zipfile
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path, PurePosixPath
from typing import assert_never

import certifi
import httpx
from pydantic import ConfigDict
from pydantic import Field as PydanticField

from btm_corekit import (
    CommandError,
    Model,
    UpstreamError,
    dump,
    parse_model,
    user_agent,
)

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

HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500

MICROMAMBA_VERSION = "2.9.0-0"
MICROMAMBA_RELEASES = (
    "https://github.com/mamba-org/micromamba-releases/releases/download"
)


def log(message: str) -> None:
    print(f"btm-setup-env: {message}", file=sys.stderr)


DIGITS_AND_DOT = frozenset("0123456789.")

# --- Downloads and extraction ---


@cache
def _client() -> httpx.Client:
    """Reads run unbounded: archives are large, links slow, and every fetch
    is resumable by re-run. Connect, write, and pool waits are bounded, so a
    dead peer fails instead of hanging."""
    return httpx.Client(
        http2=True,
        follow_redirects=True,
        timeout=httpx.Timeout(None, connect=30.0, write=30.0, pool=30.0),
        verify=ssl.create_default_context(cafile=certifi.where()),
        headers={"User-Agent": user_agent("setup-env")},
    )


def _status_failure(status: int, url: str) -> DenvError | UpstreamError:
    """A 5xx or a rate limit may clear on a retry; any other 4xx is the URL's
    own problem, and retrying changes nothing."""
    text = f"HTTP {status} fetching {url}"
    if status >= HTTP_SERVER_ERROR or status == HTTP_TOO_MANY_REQUESTS:
        return UpstreamError(text)
    return DenvError(text)


def fetch(url: str, target: Path) -> None:
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    try:
        with _client().stream("GET", url) as response:
            response.raise_for_status()
            with open(partial, "wb") as out:
                for chunk in response.iter_bytes():
                    out.write(chunk)
    except httpx.HTTPStatusError as err:
        raise _status_failure(err.response.status_code, url) from err
    except httpx.RequestError as err:
        raise UpstreamError(f"cannot reach {url}: {err}") from err
    os.replace(partial, target)


def verify_sha256(path: Path, expected: str) -> None:
    with path.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != expected:
        # Deleting the artifact is the mechanical repair: a cached corrupt
        # download would otherwise fail every re-run forever, since fetch()
        # trusts an existing file.
        path.unlink()
        raise UpstreamError(
            f"digest mismatch for {path.name}\n"
            f"  expected {expected}\n  actual   {actual}\n"
            "removed the corrupt download; re-run to fetch it again"
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
        except TypeError:  # Python <3.11.4 has no filter parameter.
            tf.extractall(dest, members=members)


INSTALL_TIMEOUT = 3600.0  # seconds; an installer past this is stuck on a lock or prompt


def run_logged(
    what: str,
    cmd: list[str],
    env: dict[str, str],
    stdin_text: str | None = None,
    timeout: float = INSTALL_TIMEOUT,
) -> None:
    """Run quietly; on failure surface the tail, which is where build tools
    put the sentence worth reading."""
    try:
        result = subprocess.run(
            cmd,
            env=env,
            input=stdin_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,  # Surface the output tail as DenvError.
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as err:
        raise UpstreamError(f"{what} produced no exit within {timeout:.0f}s") from err
    if result.returncode != 0:
        tail = "\n".join((result.stdout or "").splitlines()[-40:])
        raise DenvError(f"{what} failed (exit {result.returncode}):\n{tail}")


# --- Context ---


class Manifest(Model):
    """What a provisioned root records about itself. One reading, so status
    and the executors cannot disagree about which project it belongs to. This
    tool is the only writer and an older one may have written it, so a field
    it does not know is ignored rather than fatal."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    project: str = ""
    spec: tuple[str, ...] = ()
    host: str = ""
    conda: dict[str, tuple[str, ...]] = PydanticField(default_factory=dict)
    uv_python: str | None = None


@dataclass
class Ctx:
    layout: Layout
    host: Host
    manifest: Manifest = field(default_factory=Manifest)

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

    def record(self, **changes: object) -> None:
        self.manifest = self.manifest.with_(**changes)

    def save_manifest(self) -> None:
        path = self.layout.manifest
        partial = path.with_name(path.name + ".partial")
        partial.write_text(json.dumps(dump(self.manifest), indent=2, sort_keys=True))
        os.replace(partial, path)


def load_manifest(layout: Layout) -> Manifest:
    """A root with no manifest was never provisioned. A manifest that will not
    parse is not the same thing, so it says so rather than reading as absent
    and provoking a full reinstall."""
    try:
        raw = layout.manifest.read_text()
    except OSError:
        return Manifest()
    try:
        return parse_model(Manifest, json.loads(raw), str(layout.manifest))
    except ValueError as err:
        raise DenvError(f"unreadable {layout.manifest}: {err}") from err


# --- micromamba ---


def ensure_micromamba(ctx: Ctx) -> None:
    if ctx.mamba.exists():
        return
    platform = ctx.host.conda_platform.value
    log(f"installing micromamba {MICROMAMBA_VERSION} ({platform})")
    url = f"{MICROMAMBA_RELEASES}/{MICROMAMBA_VERSION}/micromamba-{platform}"
    archive = ctx.layout.downloads / f"micromamba-{platform}"
    fetch(url, archive)
    # Fetch the publisher digest to keep verification architecture-independent.
    sidecar = archive.with_name(archive.name + ".sha256")
    fetch(url + ".sha256", sidecar)
    try:
        verify_sha256(archive, sidecar.read_text().split()[0])
    except CommandError:
        # The sidecar itself may be the corrupt cached file; clear it too so
        # the re-run re-fetches both instead of wedging on a bad pin. Both
        # error classes land here, whichever a mismatch is later judged to be.
        sidecar.unlink(missing_ok=True)
        raise
    ctx.mamba.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, ctx.mamba)
    ctx.mamba.chmod(0o755)


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


# --- Step executors ---


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
    if python.exists() and ctx.manifest.uv_python == step.version:
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
    extract = _extract_zip if step.kind is ArchiveKind.ZIP else _extract_tar
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
    # Accept licenses silently; the install reports any failure.
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


_COMPILERS = (("cc", ("-gcc", "-clang")), ("c++", ("-g++", "-clang++")))


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


# --- aapt2 ---


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
    stable = [v for v in versions if _stable_aapt2(v)]
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


# --- Orchestration ---


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


@dataclass(frozen=True, slots=True)
class ProbeResult:
    command: tuple[str, ...]
    ok: bool
    output: str


def ensure_dirs(layout: Layout) -> None:
    for directory in (
        layout.root,
        layout.downloads,
        layout.home,
        layout.tmp,
        layout.cache,
        layout.shims,
        layout.home / ".config",
    ):
        directory.mkdir(parents=True, exist_ok=True)


def provision(plan: Plan) -> list[ProbeResult]:
    layout = plan.layout
    ensure_dirs(layout)
    ctx = Ctx(layout, plan.host, load_manifest(layout))
    ctx.record(
        project=str(plan.spec.project),
        spec=tuple(str(target) for target in plan.spec.targets),
        host=str(plan.host),
    )
    for step in plan.steps:
        execute(ctx, step)
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
                check=False,  # Report failed probes as results.
            )
        except subprocess.TimeoutExpired:
            results.append(ProbeResult(command, False, "probe timed out"))
            continue
        first = next(
            (line for line in (proc.stdout or "").splitlines() if line.strip()), ""
        )
        results.append(ProbeResult(command, proc.returncode == 0, first))
    return results


# --- Standalone foreign-binary shims ---


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
    # Merge existing packages; a second create would replace the prefix.
    existing = set(ctx.manifest.conda.get("conda/host", ()))
    merged = tuple(sorted(existing | set(host_step.packages)))
    conda_create(ctx, CondaEnv("conda/host", host.conda_platform, merged))
    conda_create(ctx, foreign_step)
    wrapper = layout.shims / binary.name
    write_qemu_wrapper(ctx, emu.qemu_binary, platform, binary.resolve(), wrapper)
    ctx.save_manifest()
    return wrapper
