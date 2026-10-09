"""The pace a service asks for, and the bounded patience its 429 earns."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError, UpstreamError
from btm_corekit.indexes import arxiv
from btm_corekit.net.pace import Pace, patient


class Clock:
    """A clock that only moves when something sleeps, so a test reads every
    wait the law asked for and spends none of them."""

    def __init__(self) -> None:
        self.now = 100.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def paced(interval: float) -> tuple[Pace, Clock]:
    clock = Clock()
    return Pace(interval, clock=clock.time, sleep=clock.sleep), clock


def throttled(status: int = 429) -> UpstreamError:
    failure = UpstreamError(f"HTTP {status} from https://x")
    failure.status = status
    return failure


class Script:
    """A call answering from a list: an exception raises, a value returns."""

    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self) -> object:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class TestPace:
    def test_the_first_call_waits_for_nothing(self):
        pace, clock = paced(3.0)
        pace.wait()
        assert clock.slept == []

    def test_a_second_call_waits_out_the_interval(self):
        """arXiv's terms ask for one request every three seconds, so the
        sleep belongs to the caller who owes it rather than to advice."""
        pace, clock = paced(3.0)
        pace.wait()
        clock.now += 1.0
        pace.wait()
        assert clock.slept == [2.0]

    def test_arxiv_owns_its_three_second_interval(self):
        assert arxiv.PACE.interval == arxiv.MIN_INTERVAL_SECONDS == 3.0


class TestPatient:
    def test_a_success_is_one_call_and_one_wait(self):
        pace, clock = paced(1.0)
        call = Script("body")
        assert patient(call, pace) == "body"
        assert call.calls == 1 and clock.slept == []

    def test_a_429_backs_off_at_double_the_previous_wait(self):
        pace, clock = paced(1.0)
        call = Script(throttled(), throttled(), "body")
        assert patient(call, pace) == "body"
        assert call.calls == 3
        assert clock.slept == [2.0, 4.0], "the pace itself is already served"

    def test_the_bound_re_raises_the_last_429(self):
        pace, clock = paced(1.0)
        last = throttled()
        call = Script(throttled(), throttled(), last, "never reached")
        with pytest.raises(UpstreamError) as raised:
            patient(call, pace)
        assert raised.value is last
        assert call.calls == 3 and clock.slept == [2.0, 4.0]

    def test_the_bound_is_the_callers(self):
        pace, _ = paced(1.0)
        call = Script(throttled(), "body")
        with pytest.raises(UpstreamError):
            patient(call, pace, attempts=1)
        assert call.calls == 1

    @pytest.mark.parametrize("failure", [throttled(503), CommandError("HTTP 404")])
    def test_another_failure_is_not_retried(self, failure):
        """Only a rate limit earns patience; a 5xx is the caller's to retry
        and a 4xx would fail the same way twice."""
        pace, clock = paced(1.0)
        call = Script(failure, "body")
        with pytest.raises(CommandError) as raised:
            patient(call, pace)
        assert raised.value is failure
        assert call.calls == 1 and clock.slept == []

    def test_no_attempt_at_all_is_a_defect(self):
        pace, _ = paced(1.0)
        with pytest.raises(ValueError, match="1 or more"):
            patient(Script("body"), pace, attempts=0)
