"""Exact refusal: filenames and paths that must never be rewritten."""

from __future__ import annotations

import re
from pathlib import Path

SENSITIVE_BASENAME_REGEX = re.compile(
    r"(?ix)^("
    r"\.env(\..+)?|\.netrc|credentials(\..+)?|secrets?(\..+)?"
    r"|passwords?(\..+)?|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?"
    r"|authorized_keys|known_hosts"
    r"|.*\.(pem|key|p12|pfx|crt|cer|jks|keystore|asc|gpg)"
    r")$"
)
SENSITIVE_PATH_COMPONENTS = frozenset({".ssh", ".aws", ".gnupg", ".kube", ".docker"})
SENSITIVE_NAME_TOKENS = (
    "secret",
    "credential",
    "password",
    "passwd",
    "apikey",
    "accesskey",
    "token",
    "privatekey",
)


def is_sensitive(path: Path) -> bool:
    """Files that must never enter a compression flow, by name alone."""
    if SENSITIVE_BASENAME_REGEX.match(path.name):
        return True
    if {p.lower() for p in path.parts} & SENSITIVE_PATH_COMPONENTS:
        return True
    collapsed = re.sub(r"[_\-\s.]", "", path.name.lower())
    return any(token in collapsed for token in SENSITIVE_NAME_TOKENS)
