"""FastAPI app: /screen (stage 1), /verify (stage 2 SSE), /providers, /health, /teacher/v1/answer."""
import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import json

from sse_starlette.sse import EventSourceResponse

from .agent import Verifier
from .linkcheck import Blocklist
from .cases import CaseStore, GemmaEncoder, JevCaseStore
from .config import ROOT, Settings, get_settings
from .guard import BudgetGuard, RateLimiter, ResultCache, clip_text
from .models import Lang, Post, Provider, ScreenResult
from .muse import MuseClient
from .screen import Screener
from .teacher import TeacherError, answer


@dataclass
class Services:
    settings: Settings
    store: CaseStore
    muse: object
    screener: Screener
    limiter: RateLimiter
    screen_limiter: RateLimiter
    budget: BudgetGuard
    verifier: Verifier
    cache: ResultCache = field(default_factory=ResultCache)

    @classmethod
    def build(cls, settings: Settings | None = None, store: CaseStore | None = None, muse=None):
        s = settings or get_settings()
        if store is None:
            store = JevCaseStore(s.data_dir / "cases.jsonl", s) if s.case_matcher == "jev" \
                else CaseStore(s.data_dir / "cases.jsonl", GemmaEncoder())
        muse = muse or MuseClient(s)
        bl = Blocklist.load(s.data_dir / "blocklist.tsv")
        return cls(settings=s, store=store, muse=muse, screener=Screener(s, store, muse, bl),
                   limiter=RateLimiter(s.verify_per_ip_hour), screen_limiter=RateLimiter(s.screen_per_ip_hour),
                   budget=BudgetGuard(s.daily_budget_usd),
                   verifier=Verifier(muse, store, bl))


def client_ip(request: Request) -> str:
    # uvicorn --proxy-headers --forwarded-allow-ips=<proxy> has already replaced request.client with the
    # address the trusted proxy reported; never read X-Forwarded-For here, a client can set it freely.
    return request.client.host if request.client else "unknown"


def spent_usd(s) -> float:
    """Every paid call this process made: Muse (stage 1, agent, search, vision) and Jev (stage 1, case match)."""
    return (getattr(s.muse, "spent_usd", 0.0) + getattr(s.screener, "jev_spent_usd", 0.0)
            + getattr(s.store, "spent_usd", 0.0))


class VerifyRequest(BaseModel):
    post: Post
    lang: Lang = "zh"
    pressure: int | None = None


class ScreenRequest(BaseModel):
    posts: list[Post] = Field(min_length=1, max_length=20)
    provider: Provider = "muse"


def create_app(services: Services | None = None) -> FastAPI:
    app = FastAPI(title="FoundFact")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["Retry-After"])
    holder: dict[str, Services] = {}

    def svc() -> Services:
        if "s" not in holder:
            holder["s"] = services or Services.build()
        return holder["s"]

    app.state.svc = svc

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/providers")
    def providers():
        return svc().screener.available()

    @app.post("/screen")
    async def screen(req: ScreenRequest, request: Request):
        s = svc()
        ip = client_ip(request)
        if not s.screen_limiter.check(ip, cost=len(req.posts)):
            return JSONResponse({"error": "rate_limited"}, status_code=429,
                                headers={"Retry-After": str(s.screen_limiter.retry_after(ip, cost=len(req.posts)))})
        paid = s.budget.allow(spent_usd(s))  # over budget: blocklist + rules only, no model calls
        results = await asyncio.gather(*(s.screener.screen_post(p, req.provider, paid=paid) for p in req.posts))
        return {"results": list(results)}

    @app.post("/verify")
    async def verify(req: VerifyRequest, request: Request):
        s = svc()
        post = req.post.model_copy(update={"text": clip_text(req.post.text, s.settings.max_chars)})
        key = ResultCache.key("\x00".join([post.text, ",".join(post.image_urls), ",".join(sorted(post.links)),
                                            ",".join(sorted(post.link_domains)), str(req.pressure)]), req.lang)
        cached = s.cache.get(key)
        if cached is None:
            if not s.limiter.check(client_ip(request)):
                return JSONResponse({"error": "rate_limited"}, status_code=429,
                                    headers={"Retry-After": str(s.limiter.retry_after(client_ip(request)))})
            if not s.budget.allow(spent_usd(s)):
                return JSONResponse({"error": "budget_exhausted"}, status_code=503)

        async def gen():
            if cached is not None:
                for name, data in cached:
                    if name == "report":
                        data = {**data, "post_id": post.id}
                    yield {"event": name, "data": json.dumps(data, ensure_ascii=False)}
                    await asyncio.sleep(0.05)
                return
            events = []
            try:
                async with asyncio.timeout(s.settings.verify_timeout_s):
                    async for name, data in s.verifier.stream(post, req.lang, req.pressure):
                        events.append((name, data))
                        yield {"event": name, "data": json.dumps(data, ensure_ascii=False)}
            except TimeoutError:
                yield {"event": "error", "data": json.dumps({"error": "timeout"})}
                return
            failed = any(n == "step" and d.get("status") == "error" for n, d in events)
            if not failed and any(n == "report" for n, _ in events):  # never replay a degraded report
                s.cache.put(key, events)
        return EventSourceResponse(gen(), ping=10)

    @app.post("/teacher/v1/answer")
    async def teacher(request: Request):
        if not svc().settings.teacher_enabled:
            raise HTTPException(404)
        if request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
            raise HTTPException(403, "teacher is local-only")
        try:
            return await answer(await request.json(), svc().muse)
        except TeacherError as e:
            raise HTTPException(400, str(e)) from e

    @app.get("/privacy", include_in_schema=False)
    def privacy():
        return FileResponse(ROOT / "web" / "privacy.html")

    @app.middleware("http")
    async def cache_headers(request: Request, call_next):
        # Cloudflare otherwise keeps JS/CSS for hours and mixes old and new files after a deploy.
        resp = await call_next(request)
        path = request.url.path
        if request.method == "GET" and "cache-control" not in resp.headers:
            if path.startswith("/shared/fonts/"):
                resp.headers["cache-control"] = "public, max-age=31536000, immutable"
            elif path == "/" or path.endswith((".html", ".js", ".css", ".png")) or path == "/privacy":
                resp.headers["cache-control"] = "no-cache"
        return resp

    app.mount("/shared", StaticFiles(directory=ROOT / "shared"), name="shared")
    app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
    return app


app = create_app()
