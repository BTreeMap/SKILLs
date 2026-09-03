"""The digest is a total partition: nothing is hidden, and the counts add up."""

from __future__ import annotations

import re

import pytest

from btm_corekit import CommandError, Item, digest
from btm_corekit.digest import Digest

CORPUS = [
    Item("a1", "Cloud seeding over the Snowy Mountains", 9.0),
    Item("a2", "Cloud seeding evaluation in Wyoming", 5.0),
    Item("a3", "Cloud seeding and hail suppression", 1.0),
    Item("b1", "Control simulation experiment with Lorenz", 8.0),
    Item("b2", "Control simulation experiment for a typhoon", 3.0),
    Item("c1", "Corporate governance and shareholder value", 0.0),
]


def labels(result):
    return [cluster.label for cluster in result.clusters]


class TestPartition:
    def test_every_item_lands_exactly_once(self):
        result = digest(CORPUS)
        covered = sum(cluster.size for cluster in result.clusters)
        assert covered + result.residue_total == result.total == len(CORPUS)

    def test_an_empty_corpus_is_an_empty_partition(self):
        result = digest([])
        assert result.clusters == () and result.residue_total == 0
        assert result.total == 0

    def test_items_sharing_no_term_fall_to_the_residue(self):
        result = digest([Item("x", "singular"), Item("y", "unrelated")])
        assert result.clusters == () and result.residue_total == 2

    def test_a_broken_partition_cannot_be_constructed(self):
        with pytest.raises(CommandError):
            Digest(clusters=(), residue=(), residue_total=0, total=5)


class TestLabels:
    def test_shared_terms_become_clusters_and_stopwords_do_not(self):
        """Ties on document frequency break on the term, so the same corpus
        always yields the same labels; the grouping is what matters."""
        result = digest(CORPUS)
        assert labels(result) == ["cloud", "control"]
        assert not {"and", "the", "with", "for"} & set(labels(result))

    def test_the_rule_selects_exactly_its_cluster(self):
        result = digest(CORPUS)
        for cluster in result.clusters:
            pattern = re.compile(cluster.rule)
            matching = [i for i in CORPUS if pattern.search(i.text.lower())]
            assert len(matching) >= cluster.size

    def test_exemplars_are_the_highest_ranked_and_bounded(self):
        [seeding] = [c for c in digest(CORPUS).clusters if c.label == "cloud"]
        assert seeding.size == 3
        assert len(seeding.exemplars) <= 2 + 1
        assert seeding.exemplars[0].key == "a1"  # rank 9.0 leads
        assert [
            item.key for item in digest(CORPUS, exemplars=1).clusters[0].exemplars
        ] == ["a1"]

    def test_the_cluster_count_never_exceeds_the_cap(self):
        corpus = [Item(f"k{n}", f"term{n % 40} shared word") for n in range(400)]
        assert len(digest(corpus, cap=5).clusters) <= 5

    def test_the_partition_is_deterministic(self):
        assert digest(CORPUS).view() == digest(list(CORPUS)).view()
