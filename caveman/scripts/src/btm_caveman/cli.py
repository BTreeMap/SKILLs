"""The command surface: verbs in, exit codes out, evidence on stdout."""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
from pathlib import Path

import btm_caveman
from btm_caveman.admit import admit
from btm_caveman.classify import NON_MARKDOWN_PROSE_EXTENSIONS
from btm_caveman.markdown import split_frontmatter
from btm_caveman.model import Plan, Refusal
from btm_caveman.store import (
    backup_base,
    load_slot,
    read_utf8,
    recorded_source,
    slot_for,
)
from btm_caveman.validate import validate
from btm_corekit import Parser, run_cli, tree_bytes, write_atomic


def print_signals(plan: Plan) -> None:
    """Hand the heuristic evidence to the agent; advisory, never blocking."""
    for note in plan.notes:
        print(f"SIGNAL: {note}")
    if plan.notes:
        print("Signals advise; the user's request decides (restore undoes everything).")


def print_format_warning(path: Path) -> None:
    if path.suffix.lower() in NON_MARKDOWN_PROSE_EXTENSIONS:
        print(
            f"WARNING: checks assume Markdown; {path.suffix} headings and code"
            " blocks are unprotected; preserve structure manually"
        )


def cmd_check(path: Path) -> int:
    match admit(path):
        case Refusal(reason):
            print(f"REFUSED: {reason}")
            return 1
        case Plan() as plan:
            fm = "yes" if plan.frontmatter else "no"
            print(f"OK: admissible (frontmatter: {fm}, body: {len(plan.body)} chars)")
            print_signals(plan)
            print_format_warning(plan.path)
            return 0


def cmd_prepare(path: Path) -> int:
    match admit(path):
        case Refusal(reason):
            print(f"REFUSED: {reason}")
            return 1
        case Plan() as plan:
            slot = slot_for(plan.path)
            recorded = recorded_source(slot)
            if recorded is not None and recorded != str(plan.path):
                print(
                    f"REFUSED: backup slot collision: {slot.directory} records"
                    f" {recorded}; refusing to touch another file's backup"
                )
                return 1
            if slot.backup_path.exists():
                print(
                    f"REFUSED: backup already exists: {slot.backup_path}\n"
                    "Remove or restore it first; refusing to overwrite a prior "
                    "original."
                )
                return 1
            slot.directory.mkdir(parents=True, exist_ok=True)
            # Identity before content: a backup must never exist anonymously.
            write_atomic(slot.meta_path, json.dumps({"source": str(plan.path)}))
            write_atomic(slot.backup_path, plan.original)
            if read_utf8(slot.backup_path) != plan.original:
                slot.backup_path.unlink(missing_ok=True)
                print("REFUSED: backup readback mismatch; aborting before any change")
                return 1
            write_atomic(slot.body_path, plan.body)
            print(f"BACKUP: {slot.backup_path}")
            print(f"BODY:   {slot.body_path}")
            print_signals(plan)
            print_format_warning(plan.path)
            print(
                "Compress the BODY file's prose, then run: "
                "apply <file> <compressed-body>"
            )
            return 0


def cmd_apply(path: Path, compressed_body_path: Path) -> int:  # noqa: PLR0911
    # Preserve each refusal's contract and exit status.
    path = path.resolve()
    slot = load_slot(path)
    if isinstance(slot, Refusal):
        print(f"REFUSED: {slot.reason}")
        return 1
    if not compressed_body_path.is_file():
        print(f"REFUSED: compressed body not found: {compressed_body_path}")
        return 1
    original = read_utf8(slot.backup_path)
    compressed_body = read_utf8(compressed_body_path)
    if original is None or compressed_body is None:
        print("REFUSED: backup or compressed body is not valid UTF-8")
        return 1
    frontmatter, original_body = split_frontmatter(original)
    if not compressed_body.strip():
        print("REFUSED: compressed body is empty")
        return 1
    if compressed_body.strip() == original_body.strip():
        print("REFUSED: output identical to input; file may already be compressed")
        return 1
    candidate = frontmatter + compressed_body
    print_format_warning(path)
    verdict = validate(original, candidate)
    for warning in verdict.warnings:
        print(f"WARNING: {warning}")
    if not verdict.is_valid:
        for error in verdict.errors:
            print(f"ERROR: {error}")
        print(
            "Target file untouched. Fix ONLY the listed errors in the compressed body"
        )
        print(
            "(restore missing content from the backup; do not recompress) and re-apply."
        )
        # Exit 1 means: fix the input and resend.
        return 1
    write_atomic(path, candidate)
    pct = round(100 * (len(original) - len(candidate)) / max(len(original), 1))
    print(f"APPLIED: {path}")
    print(f"CHARS: {len(original)} -> {len(candidate)} ({pct}% smaller)")
    print(f"BACKUP: {slot.backup_path}")
    return 0


def cmd_restore(path: Path) -> int:
    path = path.resolve()
    slot = load_slot(path)
    if isinstance(slot, Refusal):
        print(f"REFUSED: {slot.reason}")
        return 1
    original = read_utf8(slot.backup_path)
    if original is None:
        print(f"REFUSED: backup is not valid UTF-8: {slot.backup_path}")
        return 1
    write_atomic(path, original)
    print(f"RESTORED: {path} from {slot.backup_path}")
    return 0


def cmd_clean(target: Path | None) -> int:
    """Delete backup artifacts. Destroys the undo; run only on explicit request."""
    if target is None:
        base = backup_base()
        if not base.is_dir():
            print("CLEAN: no backups to remove")
            return 0
        freed = tree_bytes(base)
        shutil.rmtree(base)
        print(f"CLEAN: removed the backup tree at {base} ({freed} bytes freed)")
        return 0
    slot = slot_for(target.resolve())
    recorded = recorded_source(slot)
    if recorded is not None and recorded != str(slot.source):
        print(f"REFUSED: {slot.directory} records {recorded}; not cleaning it")
        return 1
    # Remove only the artifacts this tool writes, never an arbitrary tree.
    removed = tuple(
        p for p in (slot.backup_path, slot.body_path, slot.meta_path) if p.is_file()
    )
    freed = sum(p.stat().st_size for p in removed)
    for artifact in removed:
        artifact.unlink()
        print(f"CLEAN: removed {artifact}")
    if not removed:
        print(f"CLEAN: no backups found for {target.name}")
        return 0
    print(f"CLEAN: {freed} bytes freed")
    with contextlib.suppress(OSError):  # foreign files present: leave the directory
        slot.directory.rmdir()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(
        prog="btm-caveman",
        description=btm_caveman.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for verb, summary, run in (
        ("check", "report whether a file is admissible, with its signals", cmd_check),
        (
            "prepare",
            "back the file up and split its body out for rewriting",
            cmd_prepare,
        ),
        ("restore", "put the backed-up original back", cmd_restore),
    ):
        sub = commands.add_parser(verb, help=summary)
        sub.set_defaults(func=lambda args, run=run: run(Path(args.file)))
        sub.add_argument("file")
    apply_ = commands.add_parser(
        "apply", help="validate a compressed body and write it in place"
    )
    apply_.set_defaults(func=lambda args: cmd_apply(Path(args.file), Path(args.body)))
    apply_.add_argument("file")
    apply_.add_argument("body", help="the compressed body to validate and apply")
    clean = commands.add_parser("clean", help="remove backups for one file or --all")
    clean.set_defaults(
        func=lambda args: cmd_clean(None if args.all else Path(args.file))
    )
    target = clean.add_mutually_exclusive_group(required=True)
    target.add_argument("file", nargs="?")
    target.add_argument("--all", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_cli(build_parser(), argv)


def entrypoint() -> int:
    """Console-script boundary."""
    return main()
