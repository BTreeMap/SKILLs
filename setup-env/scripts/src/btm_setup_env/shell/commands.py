"""What a verb does: provision a plan, write its activation, probe it, or
shim one binary. The command surface calls nothing else in this package."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from btm_setup_env.catalog import qemu_steps
from btm_setup_env.model import (
    CondaPlatform,
    DenvError,
    Host,
    Layout,
    QemuUser,
    Unsupported,
    emulation,
)
from btm_setup_env.plan import Plan
from btm_setup_env.render import realize, render_ps1, render_sh
from btm_setup_env.shell.execute import conda_create, execute, write_qemu_wrapper
from btm_setup_env.shell.root import Ctx, ensure_dirs, manifest_of, read_root
from btm_setup_env.steps import (
    CondaEnv,
)


@dataclass(frozen=True, slots=True)
class ProbeResult:
    command: tuple[str, ...]
    ok: bool
    output: str


def provision(plan: Plan) -> list[ProbeResult]:
    layout = plan.layout
    ensure_dirs(layout)
    ctx = Ctx(layout, plan.host, manifest_of(read_root(layout)))
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
    ctx = Ctx(layout, host, manifest_of(read_root(layout)))
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
