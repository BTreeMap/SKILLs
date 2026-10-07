"""Argument parsing and reporting. Thin by design: parse argv, build the
pure plan, hand it to the shell, report. All policy lives below this file."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from btm_corekit import CommandError, Parser, emit, remove_tree, run_cli, signal
from btm_setup_env.catalog import CATALOG
from btm_setup_env.model import (
    CondaPlatform,
    Host,
    Layout,
    Spec,
    default_root,
    detect_host,
    find_project,
    make_spec,
    parse_tag,
    tag_name,
)
from btm_setup_env.plan import Plan, make_plan
from btm_setup_env.render import path_value
from btm_setup_env.shell.commands import ProbeResult, make_shim, provision, verify
from btm_setup_env.shell.root import Provisioned, ensure_dirs, read_root
from btm_setup_env.steps import CondaEnv, Fetch
from btm_setup_env.tags import resolve_tag


def _resolve(
    project: Path | None, root: Path | None, tags: list[str]
) -> tuple[Spec, Host, Layout]:
    """The host is read once per command, and the plan and the root agree."""
    host = detect_host()
    base = (project or find_project(Path.cwd())).resolve()
    targets = [resolve_tag(parse_tag(t)) for t in tags]
    spec = make_spec(targets, base) if targets else Spec((), base)
    return spec, host, Layout((root or default_root(base, host)).resolve())


def _build_plan(project: Path | None, root: Path | None, tags: list[str]) -> Plan:
    return make_plan(*_resolve(project, root, tags))


def _describe_step(step: object) -> str:
    match step:
        case CondaEnv(prefix_rel=p, platform=pl, packages=pkgs):
            return f"conda {p} [{pl.value if pl else 'host'}]: " + " ".join(pkgs)
        case Fetch(name=n, url=u):
            return f"fetch {n}: {u}"
        case _:
            return type(step).__name__


def cmd_design(args: argparse.Namespace) -> int:
    plan = _build_plan(args.project, args.root, args.tags)
    emit(
        {
            "root": str(plan.layout.root),
            "steps": [_describe_step(s) for s in plan.steps],
            "env": dict(plan.env.vars),
            "path": [str(p) for p in plan.env.path],
            "probes": [" ".join(p) for p in plan.probes],
        }
    )
    return 0


def _report(plan: Plan, results: list[ProbeResult]) -> int:
    """A failed probe is a finished run reporting a broken toolchain, not a
    malformed request: the record says which probe broke and exit 0 stands,
    because exit 1 means the caller can fix its own input."""
    failed = [r for r in results if not r.ok]
    repair = "re-run provision; the failed probe names what to repair"
    document: dict[str, Any] = {
        "ok": not failed,
        "root": str(plan.layout.root),
        "activate_sh": str(plan.layout.activate_sh),
        "activate_ps1": str(plan.layout.activate_ps1),
        "env": {
            **dict(plan.env.vars),
            "PATH": path_value(plan.env, plan.host),
        },
        "probes": [
            {"command": " ".join(r.command), "ok": r.ok, "output": r.output}
            for r in results
        ],
    }
    if failed:
        document["next"] = repair
        signal(f"{len(failed)} of {len(results)} probes failed; {repair}")
    emit(document)
    return 0


def cmd_provision(args: argparse.Namespace) -> int:
    plan = _build_plan(args.project, args.root, args.tags)
    return _report(plan, provision(plan))


def cmd_status(args: argparse.Namespace) -> int:
    _, _, layout = _resolve(args.project, args.root, [])
    match read_root(layout):
        case Provisioned(manifest):
            pass
        case _:
            raise CommandError(f"no environment at {layout.root}; run provision first")
    plan = _build_plan(Path(manifest.project), layout.root, list(manifest.spec))
    return _report(plan, verify(plan))


def cmd_clean(args: argparse.Namespace) -> int:
    if args.all:
        raise CommandError("no registry of roots; pass --project")
    _, _, layout = _resolve(args.project, args.root, [])
    if not layout.manifest.exists():
        raise CommandError(
            f"refusing to delete {layout.root}: no manifest.json; "
            "was this directory provisioned by btm-setup-env?"
        )
    emit(remove_tree(layout.root))
    return 0


def cmd_shim(args: argparse.Namespace) -> int:
    _, host, layout = _resolve(args.project, args.root, [])
    ensure_dirs(layout)
    wrapper = make_shim(layout, host, args.binary, CondaPlatform(args.platform))
    emit({"shim": str(wrapper)})
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    emit(
        {
            "targets": [
                {
                    "tag": tag_name(*key),
                    "summary": CATALOG[key].summary,
                    "version": CATALOG[key].version_doc,
                }
                for key in sorted(CATALOG)
            ]
        }
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    p = Parser(
        prog="btm-setup-env",
        description="Provision an isolated, userspace, per-project dev "
        "environment. Tags: family[:flavor][@version], "
        "e.g. python@3.12 kotlin:android go:cgo.",
    )
    sub = p.add_subparsers(dest="verb", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--project",
            type=Path,
            default=None,
            help="project root (default: nearest .git ancestor)",
        )
        sp.add_argument(
            "--root",
            type=Path,
            default=None,
            help="environment root (default: derived, per-project)",
        )

    for verb, summary, handler in (
        ("provision", "install the toolchains these tags name", cmd_provision),
        (
            "design",
            "show what provision would install, and install nothing",
            cmd_design,
        ),
    ):
        sp = sub.add_parser(verb, help=summary)
        sp.set_defaults(func=handler)
        sp.add_argument("tags", nargs="+", metavar="TAG")
        common(sp)
    status = sub.add_parser(
        "status", help="report what is installed and whether each probe passes"
    )
    status.set_defaults(func=cmd_status)
    common(status)
    clean = sub.add_parser("clean", help="remove the environment root for this project")
    clean.set_defaults(func=cmd_clean)
    clean.add_argument(
        "--all",
        action="store_true",
        help="refused: roots are derived per project, never listed",
    )
    common(clean)
    shim = sub.add_parser("shim", help="wrap a foreign-architecture binary to run here")
    shim.set_defaults(func=cmd_shim)
    shim.add_argument("binary", type=Path)
    shim.add_argument(
        "--platform", default="linux-64", choices=[pl.value for pl in CondaPlatform]
    )
    common(shim)
    sub.add_parser("list", help="print every known target tag").set_defaults(
        func=cmd_list
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run_cli(_parser(), argv)
    except KeyboardInterrupt:
        return 130
