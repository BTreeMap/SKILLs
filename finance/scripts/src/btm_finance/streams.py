"""Return streams, pure: pairwise correlation on common dates, effective
streams, and the correlation divisor."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import combinations

import numpy as np

from btm_finance.data.tables import Days, Floats

MIN_COMMON = 20  # common periods a correlation needs
Series = tuple[Days, Floats]
Pairs = dict[frozenset[str], float | None]


def correlation(a: Series, b: Series) -> float | None:
    """Pearson correlation on dates both series hold; null under MIN_COMMON
    common periods or zero variance. O((A + B) log(A + B))."""
    _, left, right = np.intersect1d(a[0], b[0], assume_unique=True, return_indices=True)
    x, y = a[1][left], b[1][right]
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    if x.size < MIN_COMMON or not (np.std(x) > 0.0 and np.std(y) > 0.0):
        return None
    return float(np.corrcoef(x, y)[0, 1])


def pairs_of(series: Mapping[str, Series | None]) -> Pairs:
    """Every unordered pair's correlation; null where a series is missing.
    O(S^2 T log T)."""
    found: Pairs = {}
    for one, two in combinations(sorted(series), 2):
        a, b = series[one], series[two]
        found[frozenset((one, two))] = (
            None if a is None or b is None else correlation(a, b)
        )
    return found


def effective_streams(names: Sequence[str], pairs: Pairs) -> float | None:
    """1 / mean of the correlation matrix (diagonal 1, null pairs left out),
    the mean floored at 1/n so the result lies in [1, n]. O(n^2)."""
    n = len(names)
    if n == 0:
        return None
    known = [
        value
        for one, two in combinations(names, 2)
        if (value := pairs.get(frozenset((one, two)))) is not None
    ]
    mean = (n + 2.0 * sum(known)) / (n + 2.0 * len(known))
    return 1.0 / max(mean, 1.0 / n)


def divisors(names: Sequence[str], pairs: Pairs) -> dict[str, float]:
    """Per sleeve, 1 plus the sum of its absolute correlations with the
    other sleeves; a null pair adds 0. O(n^2)."""
    return {
        name: 1.0
        + sum(
            abs(value)
            for other in names
            if other != name
            and (value := pairs.get(frozenset((name, other)))) is not None
        )
        for name in names
    }
