"""Argument surface: fetch, check, lookup, clean; one JSON document out."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import btm_asd_ste100
from btm_asd_ste100.artifacts import (
    BASE,
    SKILL,
    VERSION,
    ensure,
    fetch,
    load,
    slot_of,
    tag,
)
from btm_asd_ste100.check import Mode, allow_terms, check, limits, vocabulary
from btm_asd_ste100.records import Dictionary, Lexicon, Rules, spelled
from btm_corekit import (
    Commands,
    Optional,
    Parser,
    Required,
    add_slot,
    clean_cache,
    client_for,
    emit,
    run_cli,
    text,
)

TEXT = Required("text")
ALLOW = Optional("allow", inline=False)


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


def cmd_check(args: argparse.Namespace) -> int:
    body = text(TEXT, args)
    allowed = allow_terms(text(ALLOW, args))
    manifest = ensure(client_for(SKILL, read_timeout=None), args.version)
    lexicon = load(manifest, args.version, "lexicon.json", Lexicon)
    rules = load(manifest, args.version, "rules.json", Rules)
    lim = limits(rules, args.mode)
    report = check(body, args.mode, vocabulary(lexicon), lim, allowed)
    emit({"version": args.version, **report, "allowed": len(allowed.words)})
    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    word = args.word.strip().lower()
    manifest = ensure(client_for(SKILL, read_timeout=None), args.version)
    dictionary = load(manifest, args.version, "dictionary.json", Dictionary)
    lexicon = load(manifest, args.version, "lexicon.json", Lexicon)
    resolved = {
        (u.word, u.pos): [spelled(a) for a in u.alternatives]
        for u in lexicon.unapproved
    }
    hits = []
    for e in dictionary.entries:
        if word != e.word.lower() and word not in (f.lower() for f in e.forms):
            continue
        row = e.model_dump(exclude_none=True)
        if e.status.get("kind") == "unapproved":
            row["alternatives"] = resolved.get((e.word.lower(), e.pos), [])
        else:  # alternatives for the meanings that are not approved
            row["alternatives"] = [
                other_meaning(a) for a in e.status.get("alternatives", [])
            ]
        hits.append(row)
    document = {"version": args.version, "word": word, "entries": hits}
    if not hits:
        document["next"] = (
            "not in the dictionary: rephrase with approved words, or declare it "
            "if it is a technical noun or technical verb"
        )
    emit(document)
    return 0


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


def add_version(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--version",
        type=tag,
        default=VERSION,
        metavar="TAG",
        help=f"ste-tax release tag, default {VERSION}",
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
    add_version(checker)

    looker = commands.add_parser(
        "lookup", help="a dictionary entry and its alternatives"
    )
    looker.set_defaults(func=cmd_lookup)
    looker.add_argument("word", help="a headword or one of its forms")
    add_version(looker)

    cleaner = commands.add_parser("clean", help="drop the artifact cache")
    cleaner.set_defaults(func=cmd_clean)
    cleaner.add_argument(
        "--all", action="store_true", help="the same call: the cache is the only state"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
