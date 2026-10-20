"""One module per source: a pure parser from bytes to rows, plus a fetch that
reaches the network only through the kernel client."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from btm_corekit import CommandError, client_for

SKILL = "finance"
TIMEOUT = 60.0


def client() -> httpx.Client:
    return client_for(SKILL, read_timeout=TIMEOUT)


@dataclass
class Throttle:
    """At most one request per `interval` seconds; mutable: it holds the last
    request time."""

    interval: float
    last: float = float("-inf")
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    sleep: Callable[[float], None] = field(default=time.sleep, repr=False)

    def wait(self) -> None:
        remaining = self.interval - (self.clock() - self.last)
        if remaining > 0:
            self.sleep(remaining)
        self.last = self.clock()


def not_found(err: CommandError) -> bool:
    return err.status == 404  # noqa: PLR2004 - HTTP Not Found
