"""Probe the Muse API once per call shape and save raw responses to docs/notes/raw/."""
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import ROOT, get_settings  # noqa: E402

S = get_settings()
RAW = ROOT / "docs" / "notes" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
H = {"Authorization": f"Bearer {S.muse_api}", "Content-Type": "application/json"}
CLAIM = "網傳「台積電董事長魏哲家」在 LINE 群組帶大家買飆股，保證月報酬 30%。這是真的嗎？"


def save(name, data, dt):
    (RAW / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"== {name} ({dt:.1f}s) usage={data.get('usage') if isinstance(data, dict) else None}")


def post(path, body, name):
    t = time.time()
    r = httpx.post(f"{S.muse_base}{path}", headers=H, json=body, timeout=180)
    dt = time.time() - t
    try:
        data = r.json()
    except Exception:
        data = {"status": r.status_code, "text": r.text}
    if r.status_code >= 400:
        data = {"status": r.status_code, "body": data}
    save(name, data, dt)
    return data


def main():
    # 1. Chat Completions + json_schema
    post("/chat/completions", {
        "model": S.muse_model, "temperature": 0,
        "messages": [{"role": "system", "content": "Reply with JSON only."},
                     {"role": "user", "content": f"Does this post show scam tactics? Reply p_yes.\n<text>{CLAIM}</text>"}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": {
            "type": "object", "properties": {"p_yes": {"type": "number"}}, "required": ["p_yes"],
            "additionalProperties": False}}},
    }, "1_chat_json")

    # 2. Responses + web_search
    post("/responses", {
        "model": S.muse_model, "input": f"請查證：{CLAIM}",
        "tools": [{"type": "web_search"}], "include": ["web_search_call.results"],
    }, "2_responses_search")

    # 3. streaming event types
    t = time.time()
    types, lines = [], []
    with httpx.stream("POST", f"{S.muse_base}/responses", headers=H, timeout=180, json={
        "model": S.muse_model, "input": f"請查證：{CLAIM}", "stream": True,
        "tools": [{"type": "web_search"}]}) as r:
        for line in r.iter_lines():
            lines.append(line)
            if line.startswith("event:"):
                types.append(line[6:].strip())
            elif line.startswith("data:") and '"type"' in line:
                try:
                    types.append(json.loads(line[5:])["type"])
                except Exception:
                    pass
    seen = list(dict.fromkeys(types))
    save("3_stream_events", {"event_types": seen, "first_lines": lines[:40], "status": r.status_code}, time.time() - t)

    # 4. Responses + text.format structured
    post("/responses", {
        "model": S.muse_model, "input": f"Extract up to 3 checkable factual claims from: {CLAIM}",
        "text": {"format": {"type": "json_schema", "name": "claims", "strict": True, "schema": {
            "type": "object", "properties": {"claims": {"type": "array", "items": {"type": "string"}}},
            "required": ["claims"], "additionalProperties": False}}},
    }, "4_responses_structured")

    # 5. image understanding via chat
    post("/chat/completions", {
        "model": S.muse_model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Describe this image in one sentence."},
            {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"}}]}],
    }, "5_chat_vision")


if __name__ == "__main__":
    main()
