"""Request origin: BTM_USER_AGENT verbatim, else BTM_CONTACT, else project contact.

Origin is who the request is from. A credential is what it may spend, so
OpenAlex's key lives here beside it and travels to that host alone.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

USER_AGENT_ENV = "BTM_USER_AGENT"
CONTACT_ENV = "BTM_CONTACT"
DEFAULT_CONTACT = "skills@oss.joefang.org"
OPENALEX_KEY_ENV = "BTM_OPENALEX_KEY"


@dataclass(frozen=True, slots=True)
class CustomAgent:
    header: str


@dataclass(frozen=True, slots=True)
class Contact:
    address: str


RequestIdentity = CustomAgent | Contact


def request_identity() -> RequestIdentity:
    custom = os.environ.get(USER_AGENT_ENV)
    if custom:
        return CustomAgent(custom)
    return Contact(os.environ.get(CONTACT_ENV) or DEFAULT_CONTACT)


def user_agent(skill: str) -> str:
    match request_identity():
        case CustomAgent(header):
            return header
        case Contact(address):
            return f"btm-skills/1.0 ({skill}; mailto:{address})"


def polite_params() -> dict[str, str]:
    """The `mailto` pool parameter Crossref honors. Empty under a User-Agent
    override: the override owns identity, so nothing else marks the request."""
    match request_identity():
        case CustomAgent():
            return {}
        case Contact(address):
            return {"mailto": address}


@dataclass(frozen=True, slots=True)
class Keyed:
    key: str


@dataclass(frozen=True, slots=True)
class Trial:
    """No key: the call draws on a small daily budget, then 429s."""


OpenAlexAccess = Keyed | Trial


def openalex_access() -> OpenAlexAccess:
    """OpenAlex has required a key since 2026-02-13; its mailto pool is gone."""
    key = os.environ.get(OPENALEX_KEY_ENV)
    return Keyed(key) if key else Trial()
