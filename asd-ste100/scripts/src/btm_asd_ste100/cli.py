"""Argument surface: fetch, check, lookup, clean; one JSON document out."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import btm_asd_ste100
from btm_asd_ste100.artifacts import (
    BASE,
    SKILL,
    VERSION,
    Cached,
    Local,
    Origin,
    ensure,
    fetch,
    load,
    opened,
    slot_of,
    tag,
)
from btm_asd_ste100.check import (
    Mode,
    allow_terms,
    check,
    limits,
    stems,
    unique,
    vocabulary,
)
from btm_asd_ste100.layout import Cut, Format
from btm_asd_ste100.records import Dictionary, Entry, Lexicon, Manifest, Rules, spelled
from btm_corekit import (
    Admission,
    CommandError,
    Commands,
    Diagnostic,
    Model,
    Optional,
    Parser,
    Required,
    add_slot,
    clean_cache,
    client_for,
    emit,
    rejection,
    run_cli,
    text,
)

TEXT = Required("text")
STOP = re.compile(r"(?<=[.!?])\s+")
# An unapproved entry's alternatives, keyed like the dictionary: a word and
# part of speech can carry two qualifiers ("few" and "a few").
Resolved = dict[tuple[str, str | None, str | None], list[str]]
ALLOW = Optional("allow", inline=False)
UNCHANGED = "nothing: check writes no state"


def cmd_fetch(args: argparse.Namespace) -> int:
    manifest = fetch(client_for(SKILL, read_timeout=None), args.version)
    emit(
        {
            "version": args.version,
            "base": BASE.format(version=args.version),
            "artifacts": [
                {
                    "path": a.path,
                    "sha256": a.sha256,
                    "bytes": a.bytes,
                    "cached": str(slot_of(args.version, a.path)),
                }
                for a in manifest.artifacts
            ],
        }
    )
    return 0


def release(args: argparse.Namespace) -> tuple[Origin, Manifest]:
    """`--data DIR` reads that directory and never the network; otherwise the
    cached `--version`, fetched first when absent."""
    if args.data is not None:
        return Local(args.data), opened(args.data)
    manifest = ensure(client_for(SKILL, read_timeout=None), args.version)
    return Cached(args.version), manifest


class TextLine(Model):
    """One `--jsonl` line: a text, and the caller's key for it, echoed."""

    text: str
    id: str | int | None = None


Batch = list[tuple[int, TextLine]]  # (1-based line number, item), in input order


@dataclass(frozen=True, slots=True)
class Refused:
    """Every problem of every line; one bad line rejects the whole batch."""

    problems: list[Diagnostic]


LINE_SHAPE = '{"text": "...", "id": "..."}'


def items(raw: str) -> Batch | Refused:
    """Each non-blank line of `raw` as a `TextLine`, or every problem at once."""
    gate = Admission()
    batch: Batch = []
    for number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        where = f"line {number}"
        try:
            row = json.loads(line)
        except json.JSONDecodeError as err:
            gate.fail(where, f"make the line one JSON object: {err}", LINE_SHAPE)
            continue
        match gate.decode(TextLine, row, where, LINE_SHAPE):
            case None:
                pass
            case TextLine(text=body) if not body.strip():
                gate.fail(f"{where}.text", "give a text that is not empty")
            case item:
                batch.append((number, item))
    return Refused(gate.problems) if gate.problems else batch


def cmd_check(args: argparse.Namespace) -> int:
    """One report, or with `--jsonl` one per line from one lexicon index:
    O(lexicon) once, then O(n) per text (3,855 short texts: about 2 s)."""
    body = text(TEXT, args)
    allowed = allow_terms(text(ALLOW, args))
    batch = items(body) if args.jsonl else None
    if isinstance(batch, Refused):
        emit(rejection(batch.problems, UNCHANGED, TEXT))
        return 1
    origin, manifest = release(args)
    lexicon = load(manifest, origin, "lexicon.json", Lexicon)
    rules = load(manifest, origin, "rules.json", Rules)
    lim = limits(rules, args.mode)
    how = Cut(args.format, args.section)
    vocab = vocabulary(lexicon)
    if batch is None:
        report = check(body, vocab, lim, allowed, how)
        emit({**origin.echo(), **report, "allowed": allowed.terms})
        return 0
    reports: list[dict[str, Any]] = []
    failed: dict[str, list[int]] = {}  # message -> lines, so one cause is one fix
    for number, item in batch:
        try:
            report = check(item.text, vocab, lim, allowed, how)
        except CommandError as err:
            failed.setdefault(str(err), []).append(number)
            continue
        key = {} if item.id is None else {"id": item.id}
        reports.append({"line": number, **key, **report})
    if failed:
        problems = [
            Diagnostic(f"line{'s' * (len(ns) > 1)} {', '.join(map(str, ns))}", fix)
            for fix, ns in failed.items()
        ]
        emit(rejection(problems, UNCHANGED, TEXT))
        return 1
    emit(
        {
            **origin.echo(),
            "ok": all(r["ok"] for r in reports),
            "texts": len(reports),
            "allowed": allowed.terms,
            "reports": reports,
        }
    )
    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    origin, manifest = release(args)
    dictionary = load(manifest, origin, "dictionary.json", Dictionary)
    lexicon = load(manifest, origin, "lexicon.json", Lexicon)
    resolved = {
        (u.word, u.pos, u.qualifier): unique(map(spelled, u.alternatives))
        for u in lexicon.unapproved
    }
    by_form: dict[str, list[Entry]] = {}
    for e in dictionary.entries:
        for form in dict.fromkeys([e.word.lower(), *(f.lower() for f in e.forms)]):
            by_form.setdefault(form, []).append(e)
    # The dictionary prints no noun plurals; the lexicon derives them, and
    # `check` accepts them. Without these, `lookup valves` said "not in the
    # dictionary" for the plural of an approved noun.
    plurals = {(x.word, x.pos): x.plural.lower() for x in lexicon.approved if x.plural}
    by_plural: dict[str, list[Entry]] = {}
    for e in dictionary.entries:
        plural = plurals.get((e.word.lower(), e.pos))
        if plural and e.status.get("kind") == "approved":
            by_plural.setdefault(plural, []).append(e)
    words = [lookup_one(w, by_form, resolved, by_plural) for w in args.words]
    emit({**origin.echo(), "words": words})
    return 0


def lookup_one(
    raw: str,
    by_form: dict[str, list[Entry]],
    resolved: Resolved,
    by_plural: dict[str, list[Entry]] | None = None,
) -> dict[str, Any]:
    """Every entry whose headword or form is the word; failing that, the
    unapproved headword a regular inflection of it comes from. Then each
    approved noun whose derived plural the word is ("tests": test (v) by
    inflection, and TEST (n))."""
    word = raw.strip().lower()
    entries, headword = by_form.get(word, []), None
    if not entries:
        headword = next((b for b in stems(word) if b in by_form), None)
        entries = [
            e
            for e in by_form.get(headword or "", [])
            if e.status.get("kind") == "unapproved"
        ]
        headword = headword if entries else None
    plural_of = [e for e in (by_plural or {}).get(word, []) if e not in entries]
    hits = [entry_row(e, resolved) for e in [*entries, *plural_of]]
    document: dict[str, Any] = {"word": word, "entries": hits}
    if headword:
        document["headword"] = headword
    if not hits:
        document["next"] = (
            "not in the dictionary: rephrase with approved words, or declare it "
            "if it is a technical noun or technical verb"
        )
    return document


def entry_row(e: Entry, resolved: Resolved) -> dict[str, Any]:
    row = e.model_dump(exclude_none=True)
    if e.status.get("kind") == "unapproved":
        key = (e.word.lower(), e.pos, e.qualifier)
        row["alternatives"] = resolved.get(key, [])
        choices = paired(row["alternatives"], e.ste_example, e.nonste_example)
        if choices:
            row["choices"] = choices
            row.pop("ste_example", None)
            row.pop("nonste_example", None)
    else:  # alternatives for the meanings that are not approved
        row["alternatives"] = [
            other_meaning(a) for a in e.status.get("alternatives", [])
        ]
    return row


def paired(
    alternatives: list[str], ste: str | None, nonste: str | None
) -> list[dict[str, str]]:
    """Each alternative beside the spec's STE sentence that uses it and the
    sentence it replaces, when the spec gives one of each per alternative,
    in order; otherwise nothing, and the raw examples stay."""
    shown = example_sentences(ste)
    replaced = example_sentences(nonste)
    if not alternatives or not len(alternatives) == len(shown) == len(replaced):
        return []
    return [
        {"use": alt, "ste": s, "not_ste": n}
        for alt, s, n in zip(alternatives, shown, replaced, strict=True)
    ]


def example_sentences(text: str | None) -> list[str]:
    return [s for s in STOP.split(text.strip()) if s] if text else []


def other_meaning(alt: dict[str, str]) -> str:
    """A dictionary alternative in the lexicon's spelling."""
    match alt:
        case {"kind": "word", "word": word, "pos": pos}:
            return f"{word.lower()} ({pos})"
        case {"kind": "technical", "word": word, "class": cls}:
            return f"{word.lower()} ({cls})"
        case {"text": phrase}:
            return phrase.lower()
        case _:
            return str(alt)


def cmd_clean(args: argparse.Namespace) -> int:
    emit(clean_cache(SKILL))
    return 0


def add_version(parser: argparse._ActionsContainer) -> None:  # a parser or group
    parser.add_argument(
        "--version",
        type=tag,
        default=VERSION,
        metavar="TAG",
        help=f"ste-tax release tag, default {VERSION}",
    )


def add_release(parser: argparse.ArgumentParser) -> None:
    """`--version` or `--data`, never both: two releases for one run."""
    group = parser.add_mutually_exclusive_group()
    add_version(group)
    group.add_argument(
        "--data",
        type=Path,
        metavar="DIR",
        help="read a local ste-tax data/ directory (manifest.json and the "
        "artifacts it lists) instead of the cache, with no network",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(prog="btm-asd-ste100", description=btm_asd_ste100.__doc__)
    commands: Commands = parser.add_subparsers(dest="command", required=True)

    fetcher = commands.add_parser("fetch", help="download and verify the artifacts")
    fetcher.set_defaults(func=cmd_fetch)
    add_version(fetcher)

    checker = commands.add_parser("check", help="report STE violations in a text")
    checker.set_defaults(func=cmd_check)
    add_slot(checker, TEXT, "the text to check")
    add_slot(checker, ALLOW, "declared technical nouns and verbs, one per line")
    checker.add_argument(
        "--mode",
        type=Mode,
        choices=list(Mode),
        default=Mode.PROCEDURE,
        help="sets the sentence limit; default procedure",
    )
    checker.add_argument(
        "--format",
        type=Format,
        choices=list(Format),
        default=Format.TEXT,
        help="markdown skips front matter, code, and command payloads, and "
        "reads each heading, list item, and table row as a paragraph and each "
        "table cell as a sentence; default text",
    )
    checker.add_argument(
        "--section",
        metavar="HEADING",
        help="with --format markdown, check only this heading and its lines, "
        "up to the next heading of any level",
    )
    checker.add_argument(
        "--jsonl",
        action="store_true",
        help='the text is JSON Lines, one {"text": ..., "id": ...} object per '
        "line; one report per line under reports, the release loaded once",
    )
    add_release(checker)

    looker = commands.add_parser(
        "lookup", help="dictionary entries and their alternatives"
    )
    looker.set_defaults(func=cmd_lookup)
    looker.add_argument(
        "words", nargs="+", metavar="WORD", help="a headword or one of its forms"
    )
    add_release(looker)

    cleaner = commands.add_parser("clean", help="drop the artifact cache")
    cleaner.set_defaults(func=cmd_clean)
    cleaner.add_argument(
        "--all", action="store_true", help="the same call: the cache is the only state"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
