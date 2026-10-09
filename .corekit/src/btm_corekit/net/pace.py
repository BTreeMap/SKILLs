"""Pacing and patience: the wait a metered service asks for, and the bounded
retry its 429 earns.

Both are O(1) per call apart from the sleeping itself. The clock and the
sleep enter through fields, so the law is testable without waiting.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

from btm_corekit.net.http import HTTP_TOO_MANY_REQUESTS
from btm_corekit.report.errors import UpstreamError

T = TypeVar("T")

ATTEMPTS = 3
"""Tries per call under `patient`: the first, then two backoffs."""


def _monotonic() -> float:
    """Read at call time, so a patched `time` reaches a pace built earlier."""
    return time.monotonic()


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


@dataclass
class Pace:
    """The interval a service asks between requests, taken by the caller who
    owes it rather than left as advice to the agent. Mutable on purpose: the
    last request time is the one fact it carries."""

    interval: float
    last: float = 0.0
    clock: Callable[[], float] = field(default=_monotonic, repr=False)
    sleep: Callable[[float], None] = field(default=_sleep, repr=False)

    def wait(self) -> None:
        remaining = self.interval - (self.clock() - self.last)
        if remaining > 0:
            self.sleep(remaining)
        self.last = self.clock()


def patient(call: Callable[[], T], pace: Pace, attempts: int = ATTEMPTS) -> T:
    """Wait the pace, call, and on a 429 back off at double the previous wait,
    `attempts` tries in all; the last 429, and any other failure, re-raises."""
    if attempts < 1:
        raise ValueError(f"attempts must be 1 or more; got {attempts}")
    backoff = pace.interval
    for attempt in range(1, attempts + 1):
        pace.wait()
        try:
            return call()
        except UpstreamError as err:
            if err.status != HTTP_TOO_MANY_REQUESTS or attempt == attempts:
                raise
            backoff *= 2
            pace.sleep(backoff)
    raise AssertionError("unreachable: the loop returns or raises")
