from typing import Literal

import re

from pydantic import BaseModel, Field, field_validator, model_validator

Provider = Literal["local", "jev", "muse"]
Lang = Literal["zh", "en"]
Verdict = Literal["supported", "refuted", "insufficient", "needs_review"]


DATA_IMAGE = re.compile(r"^data:image/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$")
MAX_DATA_URL = 900_000  # nginx caps the request at 1 MB; the web app shrinks images below this


class Post(BaseModel):
    id: str
    platform: Literal["facebook", "threads", "web"]
    author: str = ""
    text: str = ""
    link_domains: list[str] = []
    links: list[str] = Field(default=[], max_length=20)  # full hrefs, for short-link resolution
    image_urls: list[str] = Field(default=[], max_length=4)  # http(s) links, or data URLs uploaded on the web
    is_sponsored: bool | None = None

    @field_validator("image_urls")
    @classmethod
    def _images(cls, v: list[str]) -> list[str]:
        for u in v:
            if u.startswith("data:"):
                if not DATA_IMAGE.match(u):
                    raise ValueError("data URL must be a base64 png, jpeg, webp or gif image")
                if len(u) > MAX_DATA_URL:
                    raise ValueError("image too large")
            elif not u.startswith(("http://", "https://")):
                raise ValueError("image must be an http(s) or data URL")
        return v

    @model_validator(mode="after")
    def _needs_content(self):
        if not self.text.strip() and not self.image_urls:
            raise ValueError("a post needs text or an image")
        return self


class Evidence(BaseModel):
    id: str
    source_type: Literal["web", "local_case", "blocklist", "image"]
    url: str | None
    title: str
    snippet: str
    date: str | None = None


class Claim(BaseModel):
    id: str
    text: str


class ClaimVerdict(BaseModel):
    claim_id: str
    verdict: Verdict
    evidence_ids: list[str]
    rationale: str


class SimilarCase(BaseModel):
    case_id: str
    title: str
    scam_type: str
    similarity: float
    url: str | None


class ScreenResult(BaseModel):
    post_id: str
    label: Literal["high", "check", "none"]
    p_scam: float
    p_claim: float
    pressure: int | None
    scam_type: str | None
    similar: list[SimilarCase]
    answered_by: Literal["proxy", "backend", "cache", "fallback", "jev", "muse", "blocklist"]
    provider: Provider
    latency_ms: int = 0
    link_hit: dict | None = None  # {"domain","category","url"} when a link is on the police fraud-domain list


class Report(BaseModel):
    post_id: str
    risk: Literal["high", "check", "low"]
    summary: str
    claims: list[Claim]
    verdicts: list[ClaimVerdict]
    evidence: list[Evidence]
    similar: list[SimilarCase]
    pressure: int | None
    actions: list[str]
    lang: Lang


class StepEvent(BaseModel):
    step: Literal["extract", "local", "search", "image", "judge", "conclude"]
    status: Literal["running", "done", "error"]
    detail: str
