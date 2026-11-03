from app.evidence import enforce_evidence
from app.models import ClaimVerdict, Evidence


def v(cid, verdict, ids):
    return ClaimVerdict(claim_id=cid, verdict=verdict, evidence_ids=ids, rationale="x")


def test_unknown_evidence_ids_downgrade():
    ev = [Evidence(id="w1", source_type="web", url="u", title="t", snippet="s")]
    out = enforce_evidence([v("c1", "refuted", ["w9"]), v("c2", "refuted", []),
                            v("c3", "refuted", ["w1", "w9"])], ev)
    assert [o.verdict for o in out] == ["insufficient", "insufficient", "refuted"]
    assert out[2].evidence_ids == ["w1"]


def test_needs_review_kept_only_with_valid_evidence():
    ev = [Evidence(id="l1", source_type="local_case", url=None, title="t", snippet="s")]
    out = enforce_evidence([v("c1", "needs_review", ["l1"]), v("c2", "needs_review", [])], ev)
    assert [o.verdict for o in out] == ["needs_review", "insufficient"]


def test_insufficient_stays_insufficient():
    out = enforce_evidence([v("c1", "insufficient", [])], [])
    assert out[0].verdict == "insufficient"
