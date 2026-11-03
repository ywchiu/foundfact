import pytest
from pydantic import ValidationError

from app.models import (ClaimVerdict, Claim, Evidence, Post, Report, ScreenResult,
                        SimilarCase, StepEvent)


def test_post_rejects_empty_text():
    with pytest.raises(ValidationError):
        Post(id="1", platform="web", text="")


def test_report_roundtrip():
    r = Report(
        post_id="p1", risk="high", summary="s",
        claims=[Claim(id="c1", text="t")],
        verdicts=[ClaimVerdict(claim_id="c1", verdict="refuted", evidence_ids=["w1"], rationale="r")],
        evidence=[Evidence(id="w1", source_type="web", url="https://x", title="t", snippet="s")],
        similar=[SimilarCase(case_id="k1", title="t", scam_type="investment", similarity=0.9, url=None)],
        pressure=2, actions=["call 165"], lang="zh",
    )
    assert Report.model_validate_json(r.model_dump_json()) == r


def test_screen_result_has_provider():
    s = ScreenResult(post_id="p", label="none", p_scam=0.1, p_claim=0.1, pressure=None,
                     scam_type=None, similar=[], answered_by="muse", provider="muse")
    assert s.provider == "muse"


def test_step_event_rejects_unknown_step():
    with pytest.raises(ValidationError):
        StepEvent(step="nope", status="done", detail="")


PNG = "data:image/png;base64," + "A" * 100


def test_post_allows_image_only():
    p = Post(id="1", platform="web", text="", image_urls=[PNG])
    assert p.text == ""


def test_post_rejects_non_image_data_url():
    with pytest.raises(ValidationError):
        Post(id="1", platform="web", text="hi", image_urls=["data:text/html;base64,PGgxPg=="])


def test_post_rejects_oversized_data_url():
    with pytest.raises(ValidationError):
        Post(id="1", platform="web", text="hi", image_urls=["data:image/jpeg;base64," + "A" * 1_000_000])


def test_post_rejects_too_many_images():
    with pytest.raises(ValidationError):
        Post(id="1", platform="web", text="hi", image_urls=[PNG] * 5)
