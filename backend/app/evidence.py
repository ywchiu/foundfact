from .models import ClaimVerdict, Evidence


def enforce_evidence(verdicts: list[ClaimVerdict], evidence: list[Evidence]) -> list[ClaimVerdict]:
    """Drop evidence ids that don't exist; any verdict left without evidence becomes insufficient."""
    known = {e.id for e in evidence}
    out = []
    for v in verdicts:
        ids = [i for i in v.evidence_ids if i in known]
        verdict = v.verdict if ids else "insufficient"
        out.append(v.model_copy(update={"evidence_ids": ids, "verdict": verdict}))
    return out
