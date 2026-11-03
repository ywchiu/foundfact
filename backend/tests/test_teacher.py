import pytest

from app import teacher
from app.teacher import QUESTIONS, TeacherError, answer


class FakeMuse:
    def __init__(self):
        self.calls = []

    async def chat_json(self, system, user, schema, name, effort="minimal", images=None):
        self.calls.append(user)
        props = schema["properties"]
        if "p_yes" in props:
            return {"p_yes": 1.7}  # out of range on purpose → must clip
        return {k: 2.0 for k in props}  # unnormalised → must normalise


async def test_noul_clipped_and_score_normalised():
    m = FakeMuse()
    out = await answer({"state": {"text": "保證獲利"}, "questions": QUESTIONS}, m)
    a = out["answers"]
    assert 0 <= a["is_scam_like"]["noul"] <= 1
    assert a["is_scam_like"]["type"] == "noul"
    probs = a["pressure"]["probabilities"]
    assert set(probs) == {"0", "1", "2", "3"}
    assert abs(sum(probs.values()) - 1) < 1e-6
    assert len(m.calls) == 3  # one Muse call per question


async def test_missing_questions_rejected():
    with pytest.raises(TeacherError):
        await answer({"state": "x", "questions": {}}, FakeMuse())
    with pytest.raises(TeacherError):
        await answer({"questions": QUESTIONS}, FakeMuse())


def test_question_ids_fixed():
    assert set(QUESTIONS) == {"is_scam_like", "has_checkable_claim", "pressure"}
    assert QUESTIONS["pressure"]["type"] == "score" and len(QUESTIONS["pressure"]["criteria"]) == 4
