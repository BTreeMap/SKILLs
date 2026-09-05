"""Argument parsing and reporting. Thin by design: parse argv, build the
pure plan, hand it to effects, report. All policy lives below this file."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from btm_corekit import Parser, dispatch
from btm_setup_env.catalog import CATALOG
from btm_setup_env.model import (
    GENERIC,
    CondaPlatform,
    DenvError,
    Layout,
    Spec,
    default_root,
    detect_host,
    find_project,
    make_spec,
    parse_tag,
)
from btm_setup_env.plan import Plan, make_plan
from btm_setup_env.render import path_value
from btm_setup_env.shell.commands import ProbeResult
from btm_setup_env.steps import CondaEnv, Fetch, stage_of
from btm_setup_env.tags import resolve_tag

VERBS = ("provision", "plan", "status", "shim", "destroy", "list")


def _resolve(
    project: Path | None, root: Path | None, tags: list[str]
) -> tuple[Spec, Layout]:
    host = detect_host()
    base = (project or find_project(Path.cwd())).resolve()
    targets = [resolve_tag(parse_tag(t)) for t in tags]
    spec = make_spec(targets, base) if targets else Spec((), base)
    return spec, Layout((root or default_root(base, host)).resolve())


def _build_plan(project: Path | None, root: Path | None, tags: list[str]) -> Plan:
    spec, layout = _resolve(project, root, tags)
    return make_plan(spec, detect_host(), layout)


def _describe_step(step: object) -> str:
    match step:
        case CondaEnv(prefix_rel=p, platform=pl, packages=pkgs):
            return f"conda {p} [{pl.value if pl else 'host'}]: " + " ".join(pkgs)
        case Fetch(name=n, url=u):
            return f"fetch {n}: {u}"
        case _:
            return type(step).__name__


def cmd_plan(args: argparse.Namespace) -> int:
    plan = _build_plan(args.project, args.root, args.tags)
    if args.json:
        print(
            json.dumps(
                {
                    "root": str(plan.layout.root),
                    "steps": [_describe_step(s) for s in plan.steps],
                    "env": dict(plan.env.vars),
                    "path": [str(p) for p in plan.env.path],
                    "probes": [" ".join(p) for p in plan.probes],
                },
                indent=2,
            )
        )
        return 0
    print(f"root: {plan.layout.root}")
    for step in plan.steps:
        print(f"  [{stage_of(step)}] {_describe_step(step)}")
    return 0


def _report(plan: Plan, results: list[ProbeResult], as_json: bool) -> int:
    ok = all(r.ok for r in results)
    if as_json:
        print(
            json.dumps(
                {
                    "ok": ok,
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
                },
                indent=2,
            )
        )
        return 0 if ok else 1
    print()
    print(f"Environment ready under {plan.layout.root}")
    print(f"  targets: {' '.join(str(t) for t in plan.spec.targets)}")
    print(f"  activate: . {plan.layout.activate_sh}")
    for r in results:
        mark = "ok " if r.ok else "FAIL"
        print(f"  {mark} {' '.join(r.command)}: {r.output}")
    if not ok:
        print(
            "some probes failed; re-running provision is the repair action",
            file=sys.stderr,
        )
    return 0 if ok else 1


def cmd_provision(args: argparse.Namespace) -> int:
    # Defer effects: importing them builds an SSL context and needs certifi.
    from btm_setup_env.shell.commands import provision  # noqa: PLC0415

    plan = _build_plan(args.project, args.root, args.tags)
    results = provision(plan)
    return _report(plan, results, args.json)


def cmd_status(args: argparse.Namespace) -> int:
    from btm_setup_env.shell.commands import verify  # noqa: PLC0415
    from btm_setup_env.shell.root import Provisioned, read_root  # noqa: PLC0415

    _, layout = _resolve(args.project, args.root, [])
    match read_root(layout):
        case Provisioned(manifest):
            pass
        case _:
            print(f"no environment at {layout.root}; run provision first")
            return 1
    plan = _build_plan(Path(manifest.project), layout.root, list(manifest.spec))
    return _report(plan, verify(plan), as_json=False)


def cmd_destroy(args: argparse.Namespace) -> int:
    _, layout = _resolve(args.project, args.root, [])
    if not layout.manifest.exists():
        raise DenvError(
            f"refusing to delete {layout.root}: no manifest.json; "
            "was this directory provisioned by btm-setup-env?"
        )
    shutil.rmtree(layout.root)
    print(f"removed {layout.root}")
    return 0


def cmd_shim(args: argparse.Namespace) -> int:
    from btm_setup_env.shell.commands import make_shim  # noqa: PLC0415
    from btm_setup_env.shell.root import ensure_dirs  # noqa: PLC0415

    _, layout = _resolve(args.project, args.root, [])
    ensure_dirs(layout)
    wrapper = make_shim(
        layout, detect_host(), args.binary, CondaPlatform(args.platform)
    )
    print(str(wrapper))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    width = max(len(_tag_of(key)) for key in CATALOG)
    for key in sorted(CATALOG):
        recipe = CATALOG[key]
        version = f"  [@{recipe.version_doc}]" if recipe.version_doc else ""
        print(f"{_tag_of(key):<{width}}  {recipe.summary}{version}")
    return 0


def _tag_of(key: tuple[str, str]) -> str:
    family, flavor = key
    return family if flavor == GENERIC else f"{family}:{flavor}"


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
        ("plan", "show what provision would install, and install nothing", cmd_plan),
    ):
        sp = sub.add_parser(verb, help=summary)
        sp.set_defaults(func=handler)
        sp.add_argument("tags", nargs="+", metavar="TAG")
        sp.add_argument("--json", action="store_true")
        common(sp)
    for verb, summary, handler in (
        (
            "status",
            "report what is installed and whether each probe passes",
            cmd_status,
        ),
        ("destroy", "remove the environment root for this project", cmd_destroy),
    ):
        sp = sub.add_parser(verb, help=summary)
        sp.set_defaults(func=handler)
        common(sp)
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


def _run(argv: list[str] | None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # A bare tag list defaults to provision.
    if argv and argv[0] not in (*VERBS, "-h", "--help"):
        argv.insert(0, "provision")
    args = _parser().parse_args(argv)
    run: Callable[[argparse.Namespace], int] = args.func
    try:
        return run(args)
    except KeyboardInterrupt:
        return 130


def main(argv: list[str] | None = None) -> int:
    return dispatch(lambda: _run(argv))
