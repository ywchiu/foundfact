"""Muse-backed answers to System One questions (hunch teacher protocol; also the `muse` stage-1 provider).

Protocol: {"state", "questions": {id: question}} -> {"answers": {id: answer}}
  noul  -> {"type":"noul","noul":p_yes}
  choice-> {"type":"choice","probabilities":{option:p}}
  score -> {"type":"score","probabilities":{"0":p,...}}
"""
import asyncio
import json

QUESTIONS: dict[str, dict] = {
    "is_scam_like": {
        "type": "noul",
        "instructions": (
            "Does this social media post show scam tactics: guaranteed returns, impersonating a "
            "celebrity/government/brand, pushing readers to LINE/private chat, suspicious links, urgent "
            "pressure to pay/act, or too-good-to-be-true jobs (easy remote/home work, high pay, no experience, "
            "apply by private message, no named company or address)? Judge only from the post itself."),
    },
    "has_checkable_claim": {
        "type": "noul",
        "instructions": (
            "Does this post state a specific factual claim that could be checked against outside sources "
            "(who said/did what, official announcements, numbers, events)?"),
    },
    "pressure": {
        "type": "score",
        "instructions": "How much urgency or pressure language does this post use?",
        "criteria": ["No pressure", "Mild promotional language", "Clear urgency or guaranteed gains",
                     "Extreme pressure: deadlines, threats, or demands to pay/transfer now"],
    },
}

SYSTEM = ("You answer one question about a piece of text. Give your probability for each answer: how likely "
          "it is to be the right one. Reply with JSON only.")


class TeacherError(ValueError):
    pass


def options(q: dict) -> list[str]:
    if q["type"] == "noul":
        return ["no", "yes"]
    crit = q["criteria"]
    return list(crit) if isinstance(crit, dict) else [str(i) for i in range(len(crit))]


def state_text(state) -> str:
    return state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)


def prompt(q: dict, text: str) -> tuple[str, dict]:
    if q["type"] == "noul":
        ask = f"{q['instructions']}\n\nReply with p_yes: the probability that the answer is yes."
        schema = {"type": "object", "properties": {"p_yes": {"type": "number"}}, "required": ["p_yes"],
                  "additionalProperties": False}
    else:
        opts = options(q)
        crit = q["criteria"] if isinstance(q["criteria"], list) else list(q["criteria"].values())
        legend = "\n".join(f"{o}: {c}" for o, c in zip(opts, crit))
        ask = f"{q['instructions']}\n\nAnswers:\n{legend}\n\nReply with a probability for each answer, summing to 1."
        schema = {"type": "object", "properties": {o: {"type": "number"} for o in opts}, "required": opts,
                  "additionalProperties": False}
    return f"{ask}\n\n<text>\n{text}\n</text>", schema


async def ask(muse, q: dict, text: str) -> dict:
    user, schema = prompt(q, text)
    reply = await muse.chat_json(SYSTEM, user, schema, "answer", effort="minimal")
    if q["type"] == "noul":
        return {"type": "noul", "noul": min(max(float(reply["p_yes"]), 0.0), 1.0)}
    opts = options(q)
    p = [max(float(reply.get(o, 0)), 0.0) for o in opts]
    total = sum(p)
    p = [x / total for x in p] if total > 0 else [1 / len(p)] * len(p)
    return {"type": q["type"], "probabilities": dict(zip(opts, p))}


async def answer(payload: dict, muse) -> dict:
    if "state" not in payload or not payload.get("questions"):
        raise TeacherError("payload needs state and at least one question")
    text = state_text(payload["state"])
    qs = payload["questions"]
    results = await asyncio.gather(*(ask(muse, q, text) for q in qs.values()))
    return {"answers": dict(zip(qs.keys(), results))}
