"""Request origin: BTM_USER_AGENT verbatim, else BTM_CONTACT, else the
project contact. Origin is who the request is from; what a request may
spend belongs to the service that meters it."""

from __future__ import annotations

import os
from dataclasses import dataclass

USER_AGENT_ENV = "BTM_USER_AGENT"
CONTACT_ENV = "BTM_CONTACT"
DEFAULT_CONTACT = "skills@oss.joefang.org"


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
    """Wikimedia blocks a request whose agent names no contact, and meters an
    anonymous one an order of magnitude tighter, so the contact is not a
    courtesy."""
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
