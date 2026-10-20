"""G4: evidence survives multiple testing. A family of 100 random signals on a
pure-noise synthetic panel yields fewer than 5 promotable standings.

Every non-statistical gate is opened first, so only DSR, PBO, the residual
t-stat, and the capacity rule decide: each run gets a critique with no
blockers and each strategy an override decision. Sizing keeps the test under
60 seconds: 60 names, 1200 trading days, monthly rebalances.
"""

from __future__ import annotations

import json
from textwrap import dedent

FAMILY = 100
RANDOM = dedent(
    '''
    import numpy as np


    def signal(market, params):
        """A fixed random score per name: a static long-short book of noise."""
        score = np.asarray([
            np.random.default_rng([SEED, *[ord(c) for c in name]]).standard_normal()
            for name in market.names
        ])
        known = np.arange(score.size)
        third = known.size // 3
        order = np.argsort(score, kind="stable")
        weights = {market.names[i]: 1.0 for i in order[-third:].tolist()}
        weights.update({market.names[i]: -1.0 for i in order[:third].tolist()})
        return weights
'''
)


def record(run, book, payload):
    code, receipt, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps(payload)
    )
    assert code == 0, err
    return receipt


def test_a_hundred_random_signals_promote_fewer_than_five(synthetic, run, families):
    book = synthetic(seed=21, names=60, days=1200, structure=False)
    families(book, noise={"trials": FAMILY})
    hypotheses = []
    for seed in range(FAMILY):
        name = f"noise-{seed}"
        folder = book / "strategies" / name
        folder.mkdir()
        (folder / "signal.py").write_text(f"SEED = {seed}\n" + RANDOM)
        config = {
            "params": {},
            "rebalance": "monthly",
            "holding_days": 21,
            "long_only": False,
            "family_id": "noise",
        }
        (folder / "config.json").write_text(json.dumps(config))
        (folder / "status").write_text("research\n")
        hypotheses.append(
            {
                "kw": ["noise", str(seed)],
                "strategy": name,
                "family_id": "noise",
                "capacity_class": "in_band",
                "falsifier": "chance",
                "counterparty": "none: planted noise",
                "min_holding_days": 21,
            }
        )
    record(run, book, {"hypotheses": hypotheses})
    run_ids = [
        run(["score", str(book), f"noise-{seed}"])[1]["run_id"]
        for seed in range(FAMILY)
    ]
    record(
        run,
        book,
        {
            "critiques": [
                {
                    "kw": ["clean", str(k)],
                    "run_id": run_id,
                    "blockers": [],
                    "concerns": [],
                    "by": "test",
                }
                for k, run_id in enumerate(run_ids)
            ],
            "decisions": [
                {
                    "kw": ["open", str(seed)],
                    "subject": f"noise-{seed}",
                    "action": "override",
                    "reason": "test opens the crowding gate",
                }
                for seed in range(FAMILY)
            ],
        },
    )
    standings = [
        run(["check", str(book), f"noise-{seed}"])[1] for seed in range(FAMILY)
    ]
    promotable = [
        view["strategy"] for view in standings if view["standing"] == "promotable"
    ]
    assert len(promotable) < 5, promotable
    assert all(view["scorecard"]["trials"] == k + 1 for k, view in enumerate(standings))
