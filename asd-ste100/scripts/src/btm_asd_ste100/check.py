"""The checker: text in, one report out. Pure; the shell supplies the
lexicon, the rules, and the allow list.

Decidable findings: sentence over the word limit (5.1 or 6.3; a note in a
procedure 25, under 5.1), paragraph over the sentence limit (6.6), a word
not approved and not allowed (1.1), an -ing form outside the approved few
(3.5), a contraction (4.2), a semicolon (8.1). Signals, never findings:
passive voice candidates (3.6), a second instruction in one sentence
(5.2), an approved word that is also an unapproved headword (1.2), an
all-caps token passed as an abbreviation. Number words pass as technical
nouns (1.5, category 9), signaled when also an unapproved headword (zero
(v)), and quoted text (1.5, category 10) is signaled, not checked. Every
finding and signal names its source line.

Cost: n tokens. Splitting and tokenizing are compiled patterns with one
class per quantifier, linear in characters and run in C; every lookup is
a set or dict probe; the approved-phrase match tries a bounded number of
phrases of bounded length per token. O(n) time and space, plus the
lexicon index, built once in O(lexicon).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import pairwise
from typing import Any

from btm_asd_ste100.layout import PARAGRAPH, Cut, layout
from btm_asd_ste100.records import Lexicon, Rules, spelled
from btm_corekit import CommandError


class Mode(StrEnum):
    PROCEDURE = "procedure"
    DESCRIPTION = "description"


Phrases = dict[str, tuple[tuple[str, ...], ...]]  # first word -> phrases, longest first

# A sentence ends at . ! ? before whitespace and a capital, digit, or
# opening mark, or before an inline code span, or at the end; at a colon
# before a list item, and before the item itself (rule 8.4: each item is a
# sentence). A colon at a wrapped line end inside prose ends nothing.
LIST_ITEM = r"\n(?=[ \t]*(?:[-*•]|\(?[0-9a-z]{1,3}[.)])[ \t])"
# A closing quotation mark or bracket after the end mark stays with the
# sentence it closes: 'SHOWS: “NO GO.” IF THERE IS' is two sentences.
CLOSING = "[\"'\u201d\u2019)\\]]*"
SENTENCE_END = re.compile(
    rf"[.!?]+{CLOSING}(?=\s+(?:`|[\"'“(\[]?[A-Z0-9]))"
    rf"|[.!?]+{CLOSING}\s*$"
    rf"|:[ \t]*(?={LIST_ITEM})"
    rf"|{LIST_ITEM}"
)
WORD = re.compile(r"[^\W_]+(?:['\-][^\W_]+)*")
# A parenthesized or quoted group counts as one word (rules 8.5, 8.6), and
# so does an inline code span, a name the reader copies whole.
GROUPED = re.compile(r"\([^()]*\)|\"[^\"]*\"|“[^”]*”|`[^`\n]*`")
# Quoted text is a technical noun (rule 1.5, category 10): counted, not checked.
QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”")
NOTE = re.compile(r"\s*note\s*:", re.IGNORECASE)
DIGIT = re.compile(r"[0-9]")
CURLY_APOSTROPHE = "\u2019"

UNITS = frozenset(
    [
        "mm",
        "cm",
        "m",
        "km",
        "in",
        "ft",
        "yd",
        "mi",
        "lb",
        "lbs",
        "oz",
        "kg",
        "g",
        "mg",
        "t",
        "n",
        "nm",
        "kn",
        "kpa",
        "mpa",
        "pa",
        "psi",
        "bar",
        "mbar",
        "v",
        "mv",
        "kv",
        "ma",
        "w",
        "kw",
        "hz",
        "khz",
        "mhz",
        "ghz",
        "s",
        "ms",
        "min",
        "h",
        "hr",
        "l",
        "ml",
        "gal",
        "qt",
        "c",
        "f",
        "k",
        "deg",
        "rpm",
        "kt",
        "kts",
        "liter",
        "liters",
        "meter",
        "meters",
        "inch",
        "inches",
        "foot",
        "feet",
        "pound",
        "pounds",
        "degree",
        "degrees",
        "second",
        "seconds",
        "minute",
        "minutes",
        "hour",
        "hours",
        "percent",
    ]
)
# Number words are technical nouns (rule 1.5, category 9) and one word
# each (rule 8.6).
NUMBERS = frozenset(
    [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
        "hundred",
        "thousand",
        "million",
        "billion",
        "half",
        "quarter",
        "first",
        "second",
        "third",
        "fourth",
        "fifth",
        "sixth",
        "seventh",
        "eighth",
        "ninth",
        "tenth",
    ]
)
TECHNICAL_NOUN = "tn"  # the part of speech rule 1.5 gives a number word
ARTICLES = frozenset(["a", "an", "the"])
BE_FORMS = frozenset(["am", "is", "are", "was", "were", "be", "been", "being"])
CONTRACTED = ("n't", "'re", "'ve", "'ll", "'d", "'m")
S_CONTRACTIONS = frozenset(
    f"{w}'s" for w in ("it", "that", "there", "here", "what", "let", "who")
)
POSSESSIVE = "'s"
ING_MIN = 5  # shorter words ending in -ing (bring, sing) are not -ing forms
DOUBLED = 3  # a stem this long may end in a doubled consonant (running)
PARTICIPLE_MIN = 5  # shorter words ending in -ed (bed, red) are not participles
PASSIVE_REACH = 2  # tokens between a form of BE and its participle, at most
CONTEXTS = 8  # distinct contexts a part-of-speech signal shows, at most
REPREFIX = "re-"  # the spec's prefix entry: use AGAIN or BACK instead


@dataclass(frozen=True, slots=True)
class Limits:
    mode: Mode
    sentence_words: int
    note_words: int | None
    paragraph_sentences: int | None
    ing_approved: frozenset[str]
    forbidden: tuple[str, ...]


def limits(rules: Rules, mode: Mode) -> Limits:
    """The parameters this mode enforces, read from rules.json. A rule
    whose parameters name a mode applies in that mode only."""
    params = [r.parameters for r in rules.rules]
    by_id = {r.id: r.parameters for r in rules.rules}

    def values(key: str) -> list[int]:
        return [p[key] for p in params if key in p and p.get("mode") in (None, mode)]

    sentence = values("max_words_per_sentence")
    paragraph = values("max_sentences_per_paragraph")
    notes = values("notes_max_words_per_sentence")
    try:
        ing = by_id["3.5"]["ing_approved"]
        forbidden = by_id["8.1"]["forbidden_punctuation"]
    except KeyError as err:
        raise CommandError(
            f"rules.json lacks a parameter the checker reads: {err}"
        ) from err
    if len(sentence) != 1:
        raise CommandError(
            f"rules.json gives {len(sentence)} sentence limits for {mode}"
        )
    return Limits(
        mode=mode,
        sentence_words=sentence[0],
        note_words=notes[0] if notes else None,
        paragraph_sentences=paragraph[0] if paragraph else None,
        ing_approved=frozenset(i.split(" (")[0] for i in ing),
        forbidden=tuple(forbidden),
    )


@dataclass(frozen=True, slots=True)
class Hint:
    """An unapproved headword a token matches, with what to write instead."""

    word: str
    pos: str | None
    alternatives: tuple[str, ...]
    note: str | None
    help: str | None


@dataclass(frozen=True, slots=True)
class Vocabulary:
    approved: frozenset[str]
    approved_pos: dict[str, frozenset[str]]
    phrases: Phrases
    unapproved: dict[str, tuple[Hint, ...]]  # by word, form, or joined phrase
    unapproved_phrases: Phrases  # headwords of two or more words
    verbs: frozenset[str]  # base form of every verb headword, approved or not
    participles: frozenset[str]


def longest_first(table: dict[str, set[tuple[str, ...]]]) -> Phrases:
    return {k: tuple(sorted(v, key=len, reverse=True)) for k, v in table.items()}


def vocabulary(lexicon: Lexicon) -> Vocabulary:
    """Index the lexicon once: O(lexicon)."""
    approved: set[str] = set()
    pos_of: dict[str, set[str]] = {}
    multi: dict[str, set[tuple[str, ...]]] = {}
    verbs: set[str] = set()
    participles: set[str] = set()
    for a in lexicon.approved:
        for form in [*a.forms, *([a.plural] if a.plural else [])]:
            if "..." in form or "…" in form:
                continue  # a template such as "as ... as"
            words = tuple(form.split())
            if len(words) > 1:
                multi.setdefault(words[0], set()).add(words)
            else:
                approved.add(form)
                pos_of.setdefault(form, set()).add(a.pos or "")
        if a.pos == "v":
            verbs.add(a.word)
            participles.update(f for f in a.forms[2:] if " " not in f)
    unapproved: dict[str, list[Hint]] = {}
    bad_multi: dict[str, set[tuple[str, ...]]] = {}
    for u in lexicon.unapproved:
        alternatives = tuple(map(spelled, u.alternatives))
        hint = Hint(u.word, u.pos, alternatives, u.note, u.help)
        words = phrase_of(u.word, u.qualifier)
        if len(words) > 1:
            bad_multi.setdefault(words[0], set()).add(words)
            unapproved.setdefault(" ".join(words), []).append(hint)
        if u.qualifier:
            continue  # "few (a few)": only the phrase is not approved
        for key in dict.fromkeys([u.word, *u.forms]):
            unapproved.setdefault(key, []).append(hint)
        if u.pos == "v":
            verbs.add(u.word)
    return Vocabulary(
        approved=frozenset(approved),
        approved_pos={k: frozenset(v) for k, v in pos_of.items()},
        phrases=longest_first(multi),
        unapproved={k: tuple(v) for k, v in unapproved.items()},
        unapproved_phrases=longest_first(bad_multi),
        verbs=frozenset(verbs),
        participles=frozenset(participles),
    )


def phrase_of(word: str, qualifier: str | None) -> tuple[str, ...]:
    """The words a headword stands for in text. A qualifier that holds the
    headword, or a form of it, is the phrase ("few", "a few"; "long", "no
    longer"); one that does not follows it ("so", "that": "so that")."""
    words = tuple(word.lower().split())
    if not qualifier:
        return words
    q = tuple(qualifier.lower().split())
    return q if " ".join(words) in " ".join(q) else words + q


@dataclass(frozen=True, slots=True)
class Allowed:
    """Declared technical nouns and verbs. A one-word term passes alone; a
    multi-word term passes only whole, so its words stay checked elsewhere."""

    words: frozenset[str]
    phrases: Phrases
    terms: int


def allow_terms(raw: str | None) -> Allowed:
    """One term per line; `#` starts a comment. A declared noun's regular
    plural passes too, on the last word of a multi-word term."""
    words: set[str] = set()
    multi: dict[str, set[tuple[str, ...]]] = {}
    terms = 0
    for line in (raw or "").replace(CURLY_APOSTROPHE, "'").splitlines():
        tokens = tuple(WORD.findall(line.split("#", 1)[0].lower()))
        terms += bool(tokens)
        if len(tokens) == 1:
            words.update((tokens[0], plural(tokens[0])))
        elif tokens:
            first = multi.setdefault(tokens[0], set())
            first.update((tokens, (*tokens[:-1], plural(tokens[-1]))))
    return Allowed(frozenset(words), longest_first(multi), terms)


def plural(noun: str) -> str:
    """Regular English plural, the rule the lexicon's derived plurals use."""
    if noun.endswith(("s", "x", "z", "ch", "sh")):
        return noun + "es"
    if noun.endswith("y") and noun[-2:-1] not in ("a", "e", "i", "o", "u"):
        return noun[:-1] + "ies"
    return noun + "s"


# ---- splitting ---------------------------------------------------------------


def paragraphs(text: str) -> list[str]:
    return [p for p in PARAGRAPH.split(text) if p.strip()]


def sentence_spans(segment: str) -> list[tuple[int, str]]:
    """Split one segment; the pieces, in order, hold every word of it, each
    with its offset in the segment."""
    out: list[tuple[int, str]] = []
    start = 0
    for end in [*(m.end() for m in SENTENCE_END.finditer(segment)), len(segment)]:
        raw = segment[start:end]
        piece = raw.strip()
        if WORD.search(piece):
            out.append((start + len(raw) - len(raw.lstrip()), piece))
        start = end
    return out


def sentences(paragraph: str) -> list[str]:
    return [piece for _, piece in sentence_spans(paragraph)]


def word_count(sentence: str) -> int:
    """Rule 8: a parenthesized or quoted group is one word, a hyphenated
    word is one word, a number with its unit is one word."""
    count, after_number = len(GROUPED.findall(sentence)), False
    for tok in WORD.findall(GROUPED.sub(" ", sentence)):
        if after_number and tok.lower() in UNITS:
            after_number = False
            continue
        count += 1
        after_number = bool(DIGIT.search(tok))
    return count


PLAIN = Cut()

# ---- the report --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Context:
    mode: Mode
    vocab: Vocabulary
    lim: Limits
    allowed: Allowed


@dataclass(slots=True)
class Report:
    findings: list[dict[str, Any]] = field(default_factory=list)
    signals: list[dict[str, Any]] = field(default_factory=list)
    words: dict[str, dict[str, Any]] = field(default_factory=dict)  # by token
    per_word: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    lines: list[int] = field(default_factory=list)  # sentence index -> line


def check(
    text: str, vocab: Vocabulary, lim: Limits, allowed: Allowed, how: Cut = PLAIN
) -> dict[str, Any]:
    """One report. `ok` is true only when no decidable finding remains."""
    text = text.replace(CURLY_APOSTROPHE, "'")
    mode = lim.mode
    cut = layout(text, how)
    ctx = Context(mode, vocab, lim, allowed)
    report = Report()
    n_words = 0
    for p_index, block in enumerate(cut.blocks):
        sents = [
            (start + offset, piece)
            for start, end in block
            for offset, piece in sentence_spans(cut.masked[start:end])
        ]
        if lim.paragraph_sentences is not None and len(sents) > lim.paragraph_sentences:
            report.findings.append({
                "rule": "6.6", "kind": "paragraph_length", "paragraph": p_index,
                "line": cut.line(sents[0][0]), "sentences": len(sents),
                "limit": lim.paragraph_sentences,
            })  # fmt: skip
        for offset, sent in sents:
            index = len(report.lines)
            report.lines.append(cut.line(offset))
            shown = text[offset : offset + len(sent)]
            n_words += measure((sent, shown), (index, p_index), ctx, report)
            scan(sent, index, ctx, report)
    report.findings.extend(report.words.values())
    report.signals.extend(report.per_word.values())
    for item in (*report.findings, *report.signals):
        locate(item, report.lines)
    skipped = [
        "meaning (1.3) and part of speech (1.2) are not decided; read the signals",
        "technical nouns and technical verbs pass only when --allow declares them",
        "text in parentheses counts as one word, not as a sentence of its own",
        "an inline code span counts as one word and its words are not checked",
    ]
    if lim.paragraph_sentences is None:
        skipped.append(f"paragraph length (6.6) does not apply in {mode} mode")
    return {
        "mode": mode.value,
        "format": how.fmt.value,
        **({"section": how.section} if how.section is not None else {}),
        "ok": not report.findings,
        "summary": summary(report),
        "limits": {
            "sentence_words": lim.sentence_words,
            "note_words": lim.note_words,
            "paragraph_sentences": lim.paragraph_sentences,
        },
        "counts": {
            "paragraphs": len(cut.blocks),
            "sentences": len(report.lines),
            "words": n_words,
        },
        "findings": report.findings,
        "signals": report.signals,
        "skipped": skipped,
    }


def locate(item: dict[str, Any], lines: list[int]) -> None:
    """Name the source line of each sentence an item cites."""
    if "sentence" in item:
        item["line"] = lines[item["sentence"]]
    elif isinstance(item.get("sentences"), list):
        item["lines"] = sorted({lines[i] for i in item["sentences"]})


def summary(report: Report) -> dict[str, Any]:
    """The report at a glance: counts by kind, and each word to replace."""

    def by_kind(items: list[dict[str, Any]]) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in items:
            out[item["kind"]] = out.get(item["kind"], 0) + 1
        return out

    return {
        "findings": by_kind(report.findings),
        "signals": by_kind(report.signals),
        "words": [f["token"] for f in report.words.values()],
    }


def measure(
    text: tuple[str, str], where: tuple[int, int], ctx: Context, report: Report
) -> int:
    """Sentence length and forbidden punctuation; returns the word count.
    `text` is the masked sentence and the source it shows; `where` is the
    sentence index and the paragraph index."""
    sent, shown = text
    index, p_index = where
    words = word_count(sent)
    limit = ctx.lim.sentence_words
    if ctx.lim.note_words is not None and NOTE.match(sent):
        limit = ctx.lim.note_words
    if words > limit:
        report.findings.append({
            "rule": "5.1" if ctx.mode is Mode.PROCEDURE else "6.3",
            "kind": "sentence_length", "sentence": index, "paragraph": p_index,
            "words": words, "limit": limit, "text": shown[:120],
        })  # fmt: skip
    for mark in ctx.lim.forbidden:
        if mark in sent:
            report.findings.append(
                {"rule": "8.1", "kind": "punctuation", "mark": mark, "sentence": index}
            )
    return words


def covered(tokens: list[str], tables: tuple[Phrases, ...]) -> set[int]:
    """Indices inside an approved or allowed multi-word term, longest first."""
    out: set[int] = set()
    for i, tok in enumerate(tokens):
        for table in tables:
            for phrase in table.get(tok, ()):
                if tuple(tokens[i : i + len(phrase)]) == phrase:
                    out.update(range(i, i + len(phrase)))
                    break
    return out


def scan(sent: str, index: int, ctx: Context, report: Report) -> None:
    """Each token, once, against the vocabulary rules; then the signals."""
    for quote in QUOTED.findall(sent):
        per_word(report, "quotation", quote, index, {
            "rule": "1.5", "text": quote,
            "evidence": "passed as quoted text, a technical noun",
        })  # fmt: skip
    originals = WORD.findall(QUOTED.sub(" ", sent))
    tokens = [t.lower() for t in originals]
    # A sentence in capitals, as in a warning, has no labels to pass. Each
    # sentence decides for itself: one shouted warning in mixed text is
    # checked, and a label in a mixed sentence passes in a shouted text.
    shouting = sum(c.isupper() for c in sent) > sum(c.islower() for c in sent)
    inside = covered(tokens, (ctx.vocab.phrases, ctx.allowed.phrases))
    inside |= phrase_findings((originals, tokens), inside, index, ctx.vocab, report)
    after_number = False
    for i, (orig, tok) in enumerate(zip(originals, tokens, strict=True)):
        number = bool(DIGIT.search(tok))
        unit = after_number and tok in UNITS
        passes = number or tok in NUMBERS or unit
        after_number = number
        if tok in NUMBERS and not unit and i not in inside:
            before = tokens[i - 1] if i else ""
            pos_signal(tok, (index, f"{before} {orig}".strip()), ctx.vocab, report)
        if passes or i in inside or tok in ctx.allowed.words:
            continue
        if tok.endswith(CONTRACTED) or tok in S_CONTRACTIONS:
            report.findings.append(
                {"rule": "4.2", "kind": "contraction", "token": orig, "sentence": index}
            )
            continue
        base = tok.removesuffix(POSSESSIVE)
        if base in ctx.allowed.words:
            continue
        if headword_compound(base, ctx.vocab):
            unknown(orig, base, index, ctx.vocab, report)
        elif approved(base, ctx.vocab):
            before = tokens[i - 1] if i else ""
            pos_signal(base, (index, f"{before} {orig}".strip()), ctx.vocab, report)
        elif compound(base, ctx):
            continue
        elif not shouting and orig.isupper() and len(orig) > 1:
            per_word(report, "abbreviation", orig, index, {
                "token": orig,
                "evidence": "all capitals in a mixed-case sentence; passed as a label",
            })  # fmt: skip
        elif base not in ctx.lim.ing_approved:
            unknown(orig, base, index, ctx.vocab, report)
    passive(tokens, index, ctx.vocab, report)
    if ctx.mode is Mode.PROCEDURE:
        instructions(tokens, index, ctx.vocab, report)


def phrase_findings(
    words: tuple[list[str], list[str]],
    inside: set[int],
    index: int,
    vocab: Vocabulary,
    report: Report,
) -> set[int]:
    """Report each unapproved multi-word headword in one sentence; return
    the token indices it covers. `words` is the tokens as written and in
    lowercase."""
    originals, tokens = words
    covers: set[int] = set()
    for start, (key, length) in bad_phrases(
        tokens, inside, vocab.unapproved_phrases
    ).items():
        shown = " ".join(originals[start : start + length])
        unknown(shown, key, index, vocab, report)
        if shown.lower() != key:
            report.words[key].setdefault("headword", key)
        covers.update(range(start, start + length))
    return covers


def bad_phrases(
    tokens: list[str], inside: set[int], table: Phrases
) -> dict[int, tuple[str, int]]:
    """Start index -> (headword, length) of each unapproved multi-word
    headword. The first word may carry a regular ending: "turned off" is
    "turn off". No match starts inside an approved or allowed term, or
    after an article: "the rear of the unit" uses the noun REAR."""
    out: dict[int, tuple[str, int]] = {}
    i = 0
    while i < len(tokens):
        hit = None
        if i not in inside and (i == 0 or tokens[i - 1] not in ARTICLES):
            firsts = dict.fromkeys(
                (tokens[i], *stems(tokens[i]), *ing_stems(tokens[i]))
            )
            hit = next(
                (
                    p
                    for first in firsts
                    for p in table.get(first, ())
                    if tuple(tokens[i + 1 : i + len(p)]) == p[1:]
                ),
                None,
            )
        if hit:
            out[i] = (" ".join(hit), len(hit))
            i += len(hit)
        else:
            i += 1
    return out


def ing_stems(tok: str) -> tuple[str, ...]:
    """Candidate bases of an -ing token, without the verb list."""
    if len(tok) < ING_MIN or not tok.endswith("ing"):
        return ()
    stem = tok[:-3]
    undoubled = (stem[:-1],) if len(stem) >= DOUBLED and stem[-1] == stem[-2] else ()
    return (stem, stem + "e", *undoubled)


def cited(item: dict[str, Any], index: int) -> None:
    """Add a sentence to an item's list once."""
    if item["sentences"][-1] != index:
        item["sentences"].append(index)


def per_word(
    report: Report, kind: str, key: str, index: int, body: dict[str, Any]
) -> None:
    """One signal per word and kind, citing every sentence it occurs in."""
    seen = report.per_word.get((kind, key))
    if seen is not None:
        cited(seen, index)
    else:
        report.per_word[(kind, key)] = {"kind": kind, **body, "sentences": [index]}


def approved(tok: str, vocab: Vocabulary) -> bool:
    """A form of an approved word; a hyphenated word passes when the whole
    is approved or every part is."""
    if tok in vocab.approved:
        return True
    parts = tok.split("-")
    return len(parts) > 1 and all(p in vocab.approved for p in parts)


def headword_compound(tok: str, vocab: Vocabulary) -> bool:
    """A hyphenated unapproved headword (air-dry): checked before its parts
    can pass as a compound of approved or declared words."""
    return "-" in tok and tok in vocab.unapproved and tok not in vocab.approved


def compound(tok: str, ctx: Context) -> bool:
    """A hyphenated word whose every part is approved, declared, or a
    number (rule 8.2: words that belong together)."""
    parts = tok.split("-")
    return len(parts) > 1 and all(
        p in ctx.vocab.approved
        or p in ctx.allowed.words
        or p in NUMBERS
        or bool(DIGIT.search(p))
        for p in parts
    )


def ing_base(tok: str, vocab: Vocabulary) -> str | None:
    """The verb headword an -ing token inflects, if any."""
    return next((b for b in ing_stems(tok) if b in vocab.verbs), None)


def stems(tok: str) -> tuple[str, ...]:
    """Candidate headwords a regular -s, -es, -ies, -ed, or -ied form comes
    from, most specific first; the spec lists no forms of unapproved words."""
    out: list[str] = []
    if tok.endswith("ies") or tok.endswith("ied"):
        out.append(tok[:-3] + "y")
    if tok.endswith("es") or tok.endswith("ed"):
        out.append(tok[:-2])
        if len(tok) > DOUBLED + 2 and tok[-3] == tok[-4] and tok.endswith("ed"):
            out.append(tok[:-3])  # planned -> plan
    if tok.endswith(("s", "d")) and not tok.endswith("ss"):
        out.append(tok[:-1])
    return tuple(out)


def unknown(orig: str, tok: str, index: int, vocab: Vocabulary, report: Report) -> None:
    """Record one occurrence of a word that is not approved; repeats of a
    word share one finding. A word that is itself an unapproved headword
    is reported under 1.1 with its alternatives, even when it ends in -ing."""
    seen = report.words.get(tok)
    if seen is not None:
        cited(seen, index)
        return
    hints = vocab.unapproved.get(tok, ())
    verb = None if hints else ing_base(tok, vocab)
    base = None
    if not hints and not verb:
        base = next((b for b in stems(tok) if b in vocab.unapproved), None)
        base = base or prefixed(tok, vocab)
        hints = vocab.unapproved.get(base, ()) if base else ()
    entry: dict[str, Any] = {
        "rule": "3.5" if verb else "1.1",
        "kind": "ing_form" if verb else "not_approved",
        "token": orig,
        "sentences": [index],
        "alternatives": unique(a for h in hints for a in h.alternatives),
    }
    if verb:
        entry["verb"] = verb
    if base:
        entry["headword"] = base
    notes = [h.note for h in hints if h.note]
    if notes:
        entry["note"] = " ".join(notes)
    helps = unique(h.help for h in hints if h.help)
    if helps:
        entry["help"] = " ".join(helps)
    if not hints and not verb:
        entry["next"] = (
            "not in the dictionary: rephrase, or declare it as a technical term"
        )
    report.words[tok] = entry


def prefixed(tok: str, vocab: Vocabulary) -> str | None:
    """The `re-` prefix entry for a word built on it (re-bind, rerun), when
    the lexicon has one; its help names what to write instead."""
    if not tok.startswith("re") or REPREFIX not in vocab.unapproved:
        return None
    rest = tok.removeprefix(REPREFIX) if tok.startswith(REPREFIX) else tok[2:]
    return REPREFIX if rest in vocab.verbs else None


def unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def pos_signal(
    tok: str, where: tuple[int, str], vocab: Vocabulary, report: Report
) -> None:
    """An approved form that is also an unapproved headword may be used in
    the part of speech that is not approved: CHECK (n) against check (v).
    `where` is the sentence index and the word with the one before it, the
    evidence for the part of speech. A number word is also a technical noun
    (zero (TN) against zero (v))."""
    index, context = where
    seen = report.per_word.get(("part_of_speech", tok))
    if seen is not None:
        cited(seen, index)
        if context not in seen["context"] and len(seen["context"]) < CONTEXTS:
            seen["context"].append(context)
        return
    poses = vocab.approved_pos.get(tok, frozenset())
    if tok in NUMBERS:
        poses |= {TECHNICAL_NOUN}
    # 'tests' is the plural of TEST (n) and the -s form of test (v): the
    # spec lists no forms of unapproved words, so try the regular stems.
    own = vocab.unapproved.get(tok) or next(
        (vocab.unapproved[b] for b in stems(tok) if b in vocab.unapproved), ()
    )
    hints = [h for h in own if h.pos not in poses]
    if hints:
        per_word(report, "part_of_speech", tok, index, {
            "rule": "1.2", "token": tok,
            "approved_as": sorted(p for p in poses if p),
            "not_approved_as": sorted({h.pos or "" for h in hints}),
            "alternatives": unique(a for h in hints for a in h.alternatives),
            "context": [context],
        })  # fmt: skip


def passive(tokens: list[str], index: int, vocab: Vocabulary, report: Report) -> None:
    """A form of BE followed, within two tokens, by a participle."""
    for i, tok in enumerate(tokens):
        if tok not in BE_FORMS:
            continue
        for j in range(i + 1, min(i + 1 + PASSIVE_REACH, len(tokens))):
            nxt = tokens[j]
            if nxt in vocab.participles or (
                nxt.endswith("ed") and len(nxt) >= PARTICIPLE_MIN
            ):
                report.signals.append({
                    "rule": "3.6", "kind": "passive_candidate", "sentence": index,
                    "evidence": " ".join(tokens[i : j + 1]),
                    "agent_named": "by" in tokens[j + 1 :],
                })  # fmt: skip
                break


def instructions(
    tokens: list[str], index: int, vocab: Vocabulary, report: Report
) -> None:
    """An approved verb right after 'and' or 'then' may open a second
    instruction (rule 5.2); a sentence that opens with 'then' has one."""
    for tok, nxt in pairwise(tokens[1:] if tokens[:1] == ["then"] else tokens):
        if tok in ("and", "then") and nxt in vocab.verbs and nxt in vocab.approved:
            report.signals.append({
                "rule": "5.2", "kind": "second_instruction", "sentence": index,
                "evidence": f"{tok} {nxt}",
            })  # fmt: skip
