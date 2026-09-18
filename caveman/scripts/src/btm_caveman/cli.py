"""The command surface: verbs in, one JSON record out, exit codes for the shell."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import btm_caveman
from btm_caveman.admit import admit
from btm_caveman.classify import NON_MARKDOWN_PROSE_EXTENSIONS
from btm_caveman.markdown import split_frontmatter
from btm_caveman.model import Plan, Refusal
from btm_caveman.store import (
    STORE,
    SlotMeta,
    load_slot,
    read_meta,
    read_utf8,
    slot_for,
)
from btm_caveman.validate import validate
from btm_corekit import (
    CommandError,
    Parser,
    Required,
    add_slot,
    emit,
    rejection,
    run_cli,
    signal,
    text,
    write_atomic,
)

BODY = Required("body", inline=False)
"""apply's compressed body: free-form prose never travels in argv."""


def send_signals(plan: Plan) -> None:
    """Hand the heuristic evidence to the agent; advisory, never blocking."""
    for note in plan.notes:
        signal(note)
    if plan.notes:
        signal("signals advise; the user's request decides (restore undoes everything)")


def warn_format(path: Path) -> None:
    if path.suffix.lower() in NON_MARKDOWN_PROSE_EXTENSIONS:
        signal(
            f"checks assume Markdown; {path.suffix} headings and code"
            " blocks are unprotected; preserve structure manually"
        )


def planned(path: Path) -> Plan:
    """The admitted plan. A refusal is an invariant, so it ends the command."""
    match admit(path):
        case Refusal(reason):
            raise CommandError(reason)
        case Plan() as plan:
            return plan


def cmd_prepare(args: argparse.Namespace) -> int:
    plan = planned(Path(args.file))
    slot = slot_for(plan.path)
    meta = read_meta(slot)
    if meta is not None and meta.source != str(plan.path):
        raise CommandError(
            f"backup slot collision: {slot.directory} records {meta.source};"
            " refusing to touch another file's backup"
        )
    if slot.backup_path.exists():
        raise CommandError(
            f"backup already exists: {slot.backup_path}; remove or restore it"
            " first, refusing to overwrite a prior original"
        )
    # Identity before content: a backup must never exist anonymously.
    STORE.write_meta(slot.directory, SlotMeta(source=str(plan.path)))
    write_atomic(slot.backup_path, plan.original)
    if read_utf8(slot.backup_path) != plan.original:
        slot.backup_path.unlink(missing_ok=True)
        raise CommandError("backup readback mismatch; aborting before any change")
    write_atomic(slot.body_path, plan.body)
    send_signals(plan)
    warn_format(plan.path)
    emit(
        {
            "file": str(plan.path),
            "backup": str(slot.backup_path),
            "body": str(slot.body_path),
            "frontmatter": bool(plan.frontmatter),
            "chars": len(plan.body),
            "next": f"compress the body file's prose, then: apply {plan.path}"
            " --body:file <compressed-body>",
        }
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    path = Path(args.file).resolve()
    slot = load_slot(path)
    # An empty body is rejected by the slot itself, before anything is read.
    compressed_body = text(BODY, args)
    original = read_utf8(slot.backup_path)
    frontmatter, original_body = split_frontmatter(original)
    if compressed_body.strip() == original_body.strip():
        raise CommandError("output identical to input; file may already be compressed")
    candidate = frontmatter + compressed_body
    warn_format(path)
    verdict = validate(original, candidate)
    for warning in verdict.warnings:
        signal(warning)
    if not verdict.is_valid:
        # Every fix in one verdict; the target file stays as it was.
        emit(rejection(verdict.errors, "target file", BODY))
        return 1
    write_atomic(path, candidate)
    percent = round(100 * (len(original) - len(candidate)) / max(len(original), 1))
    emit(
        {
            "file": str(path),
            "backup": str(slot.backup_path),
            "chars_before": len(original),
            "chars_after": len(candidate),
            "percent_smaller": percent,
        }
    )
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    path = Path(args.file).resolve()
    slot = load_slot(path)
    write_atomic(path, read_utf8(slot.backup_path))
    emit({"file": str(path), "backup": str(slot.backup_path)})
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """List the backups, or delete some. Deletion destroys the undo, so it
    runs only on an explicit request."""
    if args.file is None:
        listing = STORE.clean(None, args.all)
        # A slot is addressed by the file it backs up, never by its own name.
        emit(
            listing
            if args.all
            else listing | {"next": "pass a file path to remove its backup, or --all"}
        )
        return 0
    target = Path(args.file).resolve()
    slot = slot_for(target)
    meta = read_meta(slot)
    if meta is not None and meta.source != str(target):
        raise CommandError(f"{slot.directory} records {meta.source}; not cleaning it")
    # Removal demands the marker, so only what prepare wrote can be removed.
    emit(STORE.clean(str(slot.directory), args.all))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(
        prog="btm-caveman",
        description=btm_caveman.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for verb, summary, run in (
        (
            "prepare",
            "back the file up and split its body out for rewriting",
            cmd_prepare,
        ),
        ("restore", "put the backed-up original back", cmd_restore),
    ):
        sub = commands.add_parser(verb, help=summary)
        sub.set_defaults(func=run)
        sub.add_argument("file")
    applier = commands.add_parser(
        "apply", help="validate a compressed body and write it in place"
    )
    applier.set_defaults(func=cmd_apply)
    applier.add_argument("file")
    add_slot(applier, BODY, "the compressed body, frontmatter excluded")
    cleaner = commands.add_parser(
        "clean", help="list backups with sizes; remove one file's or --all"
    )
    cleaner.set_defaults(func=cmd_clean)
    cleaner.add_argument("file", nargs="?")
    cleaner.add_argument("--all", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)


def entrypoint() -> int:
    """Console-script boundary."""
    return main()
