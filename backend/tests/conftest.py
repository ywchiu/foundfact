import json

import pytest

from app.cases import CaseStore
from app.config import Settings
from tests.test_cases import ROWS, FakeEncoder


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, muse_api="k", typesafe_api_key="", openrouter_key="", data_dir=tmp_path)


@pytest.fixture
def store(tmp_path):
    p = tmp_path / "cases.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in ROWS))
    return CaseStore(p, FakeEncoder())


class FakeMuse:
    """Answers stage-1 questions from keywords; records calls."""

    def __init__(self, p_scam=0.9, p_claim=0.3):
        self.p_scam, self.p_claim = p_scam, p_claim
        self.calls = 0
        self.spent_usd = 0.0

    async def chat_json(self, system, user, schema, name, effort="minimal", images=None):
        self.calls += 1
        props = schema["properties"]
        if "p_yes" in props:
            return {"p_yes": self.p_scam if "scam tactics" in user else self.p_claim}
        return {"0": 0.1, "1": 0.2, "2": 0.6, "3": 0.1}


@pytest.fixture
def fake_muse():
    return FakeMuse()
