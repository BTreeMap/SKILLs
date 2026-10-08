"""Wire shapes of the ste-tax artifacts. Another repository writes them, so
every model ignores fields it does not read."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, StringConstraints

from btm_corekit import Model

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Wire(Model):
    model_config = ConfigDict(frozen=True, extra="ignore")


class Artifact(Wire):
    path: Annotated[str, StringConstraints(pattern=r"^data/[a-z_]+\.json$")]
    sha256: Sha256
    bytes: Annotated[int, Field(ge=0)]


class Manifest(Wire):
    schema_version: Literal[1]
    artifacts: list[Artifact]


class Approved(Wire):
    id: str
    word: str
    pos: str | None
    forms: list[str]
    plural: str | None = None


class RefAlt(Wire):
    """An approved entry; `form` when the spec names an inflection of it,
    `stated_pos` when the spec tags it with a part of speech it lacks."""

    ref: str
    form: str | None = None
    stated_pos: str | None = None


class TechnicalAlt(Wire):
    technical: str
    class_: Annotated[str, Field(alias="class")]


class PhraseAlt(Wire):
    phrase: str


Alternative = RefAlt | TechnicalAlt | PhraseAlt


class Unapproved(Wire):
    word: str
    pos: str | None
    qualifier: str | None = None
    forms: list[str] = Field(default_factory=list)
    alternatives: list[Alternative]
    note: str | None = None


class Lexicon(Wire):
    schema_version: Literal[1]
    approved: list[Approved]
    unapproved: list[Unapproved]


class Rule(Wire):
    id: str
    title: str
    paraphrase: str
    check: str
    parameters: dict[str, Any]


class Rules(Wire):
    schema_version: Literal[1]
    rules: list[Rule]


class Entry(Wire):
    """One dictionary headword; `status` is passed through to `lookup`."""

    word: str
    pos: str | None
    qualifier: str | None = None
    forms: list[str] = Field(default_factory=list)
    status: dict[str, Any]
    ste_example: str | None = None
    nonste_example: str | None = None
    page: str | None = None


class Dictionary(Wire):
    schema_version: Literal[1]
    entries: list[Entry]


def spelled(alt: Alternative) -> str:
    """An alternative as a writer reads it: `fast (adj): faster`,
    `cover (TN)`, `at the same time`."""
    match alt:
        case RefAlt(ref=ref, form=None):
            return ref
        case RefAlt(ref=ref, form=form):
            return f"{ref}: {form}"
        case TechnicalAlt(technical=word, class_=cls):
            return f"{word} ({cls.upper()})"
        case PhraseAlt(phrase=phrase):
            return phrase
