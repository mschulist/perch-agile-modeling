"""Retry behaviour of the Xeno-canto lookup, without touching the network."""

from dataclasses import dataclass, field

import httpx
import pytest

from perch_analyzer.app_context import AppContext
from perch_analyzer.target_recordings import xenocanto


@dataclass
class FakeXenoCanto:
    """Answers with `codes` in order, repeating the last one."""

    codes: list[int] = field(default_factory=list)
    calls: int = 0

    def get(self, url: str) -> httpx.Response:
        self.calls += 1
        code = self.codes[min(self.calls, len(self.codes)) - 1]
        body = {"recordings": [{"id": "123"}]} if code == 200 else {}
        return httpx.Response(code, json=body)


def _no_sleep(seconds: float) -> None:
    pass


def _sci_name(ebird_6_code: str) -> str:
    return "Cyanocitta stelleri"


@pytest.fixture
def xc(monkeypatch: pytest.MonkeyPatch) -> FakeXenoCanto:
    fake = FakeXenoCanto()
    monkeypatch.setattr(xenocanto.httpx, "get", fake.get)
    monkeypatch.setattr(xenocanto.time, "sleep", _no_sleep)
    monkeypatch.setattr(xenocanto, "convert_ebird_6_code_to_xc_sci_name", _sci_name)
    return fake


def _get(ctx: AppContext) -> list[str]:
    return xenocanto.get_xc_ids(ctx.config, "stejay", "song")


def test_retries_rate_limiting_then_succeeds(xc: FakeXenoCanto, ctx: AppContext):
    xc.codes = [429, 503, 200]
    assert _get(ctx) == ["123"]
    assert xc.calls == 3


def test_a_404_fails_immediately(xc: FakeXenoCanto, ctx: AppContext):
    """This used to retry forever."""
    xc.codes = [404]
    with pytest.raises(ValueError, match="status code: 404"):
        _get(ctx)
    assert xc.calls == 1


def test_persistent_server_errors_give_up(xc: FakeXenoCanto, ctx: AppContext):
    xc.codes = [500]
    with pytest.raises(ValueError, match="status code: 500"):
        _get(ctx)
    assert xc.calls == xenocanto.MAX_ATTEMPTS


def test_unauthorized_explains_the_api_key(xc: FakeXenoCanto, ctx: AppContext):
    xc.codes = [401]
    with pytest.raises(ValueError, match="API key"):
        _get(ctx)
    assert xc.calls == 1
