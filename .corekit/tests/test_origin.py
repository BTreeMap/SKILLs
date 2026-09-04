"""Request-origin chain: verbatim override, else contact, else project floor."""

from __future__ import annotations

from btm_corekit import Keyed, Trial, openalex_access, request_identity, user_agent


class TestRequestIdentity:
    def test_a_verbatim_override_wins(self, monkeypatch):
        monkeypatch.setenv("BTM_USER_AGENT", "my-agent/2")
        monkeypatch.setenv("BTM_CONTACT", "me@example.org")
        assert user_agent("alpha") == "my-agent/2"

    def test_a_contact_derives_the_header(self, monkeypatch):
        monkeypatch.delenv("BTM_USER_AGENT", raising=False)
        monkeypatch.setenv("BTM_CONTACT", "me@example.org")
        assert user_agent("alpha") == "btm-skills/1.0 (alpha; mailto:me@example.org)"

    def test_the_project_contact_is_the_floor(self, monkeypatch):
        monkeypatch.delenv("BTM_USER_AGENT", raising=False)
        monkeypatch.delenv("BTM_CONTACT", raising=False)
        assert "skills@oss.joefang.org" in request_identity().address


class TestOpenAlexAccess:
    def test_a_key_is_carried(self, monkeypatch):
        monkeypatch.setenv("BTM_OPENALEX_KEY", "k-123")
        assert openalex_access() == Keyed("k-123")

    def test_no_key_is_the_trial_budget(self, monkeypatch):
        monkeypatch.delenv("BTM_OPENALEX_KEY", raising=False)
        assert isinstance(openalex_access(), Trial)
