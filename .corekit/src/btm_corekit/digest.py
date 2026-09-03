"""A projection sized to a judgment rather than to the corpus.

An agent screening a few hundred candidates does not need the rows; it needs
to know what kinds of thing are in there, and to accept or reject a kind in
one move. Reading rows costs the agent tokens proportional to the corpus,
which is the wrong asymptote for a decision whose real arity is the number of
kinds. `digest` computes that partition here, in C-backed passes, and hands
back one label, one count, one selecting rule, and a few exemplars per kind.

The partition is total, so nothing is hidden: every item lands in exactly one
cluster or in the residue, and the counts add up to the input size.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from heapq import nlargest
from typing import Any

from btm_corekit.invariants import require
from btm_corekit.text import ascii_words

CLUSTER_CAP = 20  # how many kinds an agent can weigh in one pass
EXEMPLARS = 2  # enough rows to judge a label, not enough to read the corpus
CLUSTER_SIZE_MIN = 2  # one item is that item, not a kind worth a rule
TEXT_CHARS = 90  # an exemplar identifies its cluster; it is not the record
RESIDUE_CAP = 25
LABEL_CHARS_MIN = 3  # shorter tokens are articles and initials, never kinds
LABEL_SHARE_MAX = 0.6  # a term in most items separates nothing
LABEL_ITEMS_MIN = 2  # a term in one item names that item, not a kind

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "there",
        "these",
        "this",
        "to",
        "was",
        "were",
        "which",
        "with",
        "within",
        "without",
        "using",
        "use",
        "used",
        "based",
        "toward",
        "towards",
        "over",
        "under",
        "between",
        "during",
        "new",
        "novel",
        "study",
        "studies",
        "analysis",
        "approach",
        "method",
        "methods",
        "model",
        "models",
        "results",
    ]
)


@dataclass(frozen=True, slots=True)
class Item:
    """One undecided thing: the key a rule would select, the text that
    describes it, and the rank deciding which items represent their cluster."""

    key: str
    text: str
    rank: float = 0.0


def brief(item: Item) -> dict[str, str]:
    """An item as a projection carries it: enough text to recognize the kind,
    truncated because the caller reads dozens of these and reads the record
    itself only for the few it then acts on."""
    text = item.text
    if len(text) > TEXT_CHARS:
        text = text[:TEXT_CHARS].rstrip() + "..."
    return {"key": item.key, "text": text}


@dataclass(frozen=True, slots=True)
class Cluster:
    """A set of items sharing one term, judgeable as a unit. `rule` selects
    exactly `size` items, so accepting or rejecting the cluster is one
    operation rather than `size` of them."""

    label: str
    size: int
    rule: str
    exemplars: tuple[Item, ...]

    def view(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "size": self.size,
            "rule": self.rule,
            "exemplars": [brief(item) for item in self.exemplars],
        }


@dataclass(frozen=True, slots=True)
class Digest:
    """A total partition of the undecided set: every item is in exactly one
    cluster or in the residue, and `covered + residue_total == total`."""

    clusters: tuple[Cluster, ...]
    residue: tuple[Item, ...]
    residue_total: int
    total: int

    def __post_init__(self) -> None:
        covered = sum(cluster.size for cluster in self.clusters)
        require(
            covered + self.residue_total == self.total,
            "a digest partitions its input: clusters plus residue is the total",
        )

    def view(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "clusters": [cluster.view() for cluster in self.clusters],
            "residue": [brief(item) for item in self.residue],
            "residue_total": self.residue_total,
        }


def _labels(items: list[tuple[Item, list[str]]], cap: int) -> list[str]:
    """Terms that partition the set: seen at least twice, in at most
    `LABEL_SHARE_MAX` of items, ranked by document frequency. Ties break on
    the term itself so the same corpus always yields the same digest."""
    frequency: Counter[str] = Counter()
    for _, words in items:
        frequency.update(
            word
            for word in set(words)
            if len(word) >= LABEL_CHARS_MIN and word not in STOPWORDS
        )
    ceiling = max(LABEL_ITEMS_MIN, int(len(items) * LABEL_SHARE_MAX))
    usable = sorted(
        (-count, term)
        for term, count in frequency.items()
        if LABEL_ITEMS_MIN <= count <= ceiling
    )
    return [term for _, term in usable[:cap]]


def rank_of(item: Item) -> float:
    return item.rank


def digest(
    items: list[Item],
    *,
    cap: int = CLUSTER_CAP,
    exemplars: int = EXEMPLARS,
    residue_cap: int = RESIDUE_CAP,
) -> Digest:
    """Partition `items` by their most distinguishing shared term.

    One `ascii_words` pass per item, one document-frequency count, one
    assignment pass, then a bounded top-k per cluster: O(n*w + V log V) for n
    items of w words over a vocabulary of V terms, and O(V) space. At the
    sizes this serves (hundreds of items, thousands of terms) that is
    microseconds against the thousands of tokens it saves the caller.
    """
    tokenized = [(item, ascii_words(item.text)) for item in items]
    ranked = _labels(tokenized, cap)
    order = {term: index for index, term in enumerate(ranked)}
    buckets: defaultdict[str, list[Item]] = defaultdict(list)
    residue: list[Item] = []
    for item, words in tokenized:
        hits = [order[word] for word in set(words) if word in order]
        if hits:
            buckets[ranked[min(hits)]].append(item)
        else:
            residue.append(item)
    clusters: list[Cluster] = []
    for term in ranked:
        members = buckets.get(term)
        if not members:
            continue
        # A cluster too small to deserve a rule is noise in the decision
        # surface: fold it back so the caller sees the items themselves.
        if len(members) < CLUSTER_SIZE_MIN:
            residue.extend(members)
            continue
        clusters.append(
            Cluster(
                label=term,
                size=len(members),
                rule=f"\\b{term}\\b",
                exemplars=tuple(nlargest(exemplars, members, key=rank_of)),
            )
        )
    return Digest(
        clusters=tuple(clusters),
        residue=tuple(residue[:residue_cap]),
        residue_total=len(residue),
        total=len(items),
    )
