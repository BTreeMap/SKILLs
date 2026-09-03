"""Exact refusal: filenames and paths that must never be rewritten."""

from __future__ import annotations

from pathlib import Path

# Basenames refused outright: exact names, names with a dotted suffix, key
# files with an optional `.pub`, and anything carrying a secret-bearing extension.
SENSITIVE_EXACT = frozenset({".netrc", "authorized_keys", "known_hosts"})
SENSITIVE_STEMS = (".env", "credentials", "secret", "secrets", "password", "passwords")
KEY_STEMS = tuple(f"id_{algo}" for algo in ("rsa", "dsa", "ecdsa", "ed25519"))
SENSITIVE_SUFFIXES = tuple(
    f".{ext}"
    for ext in (
        "pem",
        "key",
        "p12",
        "pfx",
        "crt",
        "cer",
        "jks",
        "keystore",
        "asc",
        "gpg",
    )
)


def _stem_matches(name: str, stem: str) -> bool:
    """`stem` alone, or `stem.` followed by at least one character."""
    return name == stem or (name.startswith(stem + ".") and len(name) > len(stem) + 1)


def sensitive_basename(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered in SENSITIVE_EXACT
        or any(_stem_matches(lowered, stem) for stem in SENSITIVE_STEMS)
        or any(lowered in (stem, stem + ".pub") for stem in KEY_STEMS)
        or lowered.endswith(SENSITIVE_SUFFIXES)
    )


_JOINERS = str.maketrans("", "", "_- \t.")
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
    if sensitive_basename(path.name):
        return True
    if {p.lower() for p in path.parts} & SENSITIVE_PATH_COMPONENTS:
        return True
    collapsed = path.name.lower().translate(_JOINERS)
    return any(token in collapsed for token in SENSITIVE_NAME_TOKENS)
