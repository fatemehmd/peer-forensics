"""Branch-point resampling: replay a saved rollout up to just BEFORE its first contact with the shared cache,
then regenerate the remainder N times, optionally with the shared-cache contents swapped to another condition.
The pre-exposure prefix is held fixed; exposure and everything after is fresh.

Usage: python resample.py results/<rollout>.json --n 20 --swap-to solo_info_success
"""
import argparse, asyncio, json, os, sys
from openai import AsyncOpenAI
import env as E

def branch_prefix(rec, swap_to):
    """Rebuild the message list up to (NOT including) the first turn that touches the shared cache.
    Everything the agent saw before any exposure is held fixed; the exposure and all later turns are regenerated."""
    env = E.Env(swap_to or rec["condition"], report_tool=rec.get("report_tool", True))
    sysp = E.SYSTEM_PROMPT if env.report_tool else E.SYSTEM_PROMPT_NOREPORT
    msgs = [{"role": "system", "content": sysp}, {"role": "user", "content": env.initial_user_message()}]
    def touches_shared(tc):
        a = json.dumps(tc["args"])
        return "/shared/cache" in a or "artifact-cache.internal" in a
    bt = None
    for t in rec["transcript"]:
        if any(touches_shared(tc) for tc in t["tool_calls"]): bt = t["turn"]; break
    if bt is None: raise SystemExit("rollout never touched the shared cache; nothing to branch on")
    for t in rec["transcript"]:
        if t["turn"] >= bt: break
        am = {"role": "assistant", "content": t["content"] or ""}
        if t["reasoning"]: am["reasoning"] = t["reasoning"]
        am["tool_calls"] = [{"id": f"call_{t['turn']}_{i}", "type": "function",
                             "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])}} for i, tc in enumerate(t["tool_calls"])]
        msgs.append(am)
        for i, tc in enumerate(t["tool_calls"]):
            out = env.call(tc["name"], tc["args"])
            msgs.append({"role": "tool", "tool_call_id": f"call_{t['turn']}_{i}", "content": out})
    return msgs, env, bt

async def continue_rollout(client, model, msgs, env, k, effort, max_turns=25):
    msgs = json.loads(json.dumps(msgs)); env = env  # env is fresh per call (built in caller)
    transcript = []
    for turn in range(max_turns):
        r = await client.chat.completions.create(model=model, messages=msgs, tools=E.tools_for(env.report_tool),
                                                 temperature=1.0, extra_body={"reasoning": {"effort": effort}})
        m = r.choices[0].message
        reasoning = getattr(m, "reasoning", None) or (m.model_extra or {}).get("reasoning")
        am = {"role": "assistant", "content": m.content or ""}
        if reasoning: am["reasoning"] = reasoning
        entry = dict(turn=turn, reasoning=reasoning, content=m.content, tool_calls=[])
        if m.tool_calls: am["tool_calls"] = [tc.model_dump() for tc in m.tool_calls]
        msgs.append(am)
        if not m.tool_calls: transcript.append(entry); break
        for tc in m.tool_calls:
            try: args = json.loads(tc.function.arguments or "{}")
            except Exception: args = {}
            out = env.call(tc.function.name, args)
            entry["tool_calls"].append(dict(name=tc.function.name, args=args, result=out[:500]))
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": out})
        transcript.append(entry)
        if env.done: break
    return dict(k=k, metrics=env.metrics, transcript=transcript)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rollout"); ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--swap-to", default=None, help="condition whose board/README replaces the original in the prefix")
    ap.add_argument("--effort", default="medium"); ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"))
    a = ap.parse_args()
    rec = json.load(open(a.rollout))
    client = AsyncOpenAI(base_url=a.base_url, api_key=os.environ.get("OPENROUTER_API_KEY", "EMPTY"))
    sem = asyncio.Semaphore(a.concurrency)
    async def one(k):
        async with sem:
            msgs, env, bt = branch_prefix(rec, a.swap_to)
            return await continue_rollout(client, rec["model"], msgs, env, k, a.effort)
    outs = await asyncio.gather(*[one(k) for k in range(a.n)])
    _, _, bt = branch_prefix(rec, a.swap_to)
    tag = f"__swap_{a.swap_to}" if a.swap_to else "__same"
    fn = a.rollout.replace(".json", f"{tag}__branch{bt}.resample.json")
    json.dump(dict(source=a.rollout, swap_to=a.swap_to, branch_turn=bt, samples=outs), open(fn, "w"), indent=1)
    p = sum(o["metrics"]["used_proxy"] for o in outs); r = sum(o["metrics"]["reported"] for o in outs)
    print(f"branch turn {bt} swap={a.swap_to}: used_proxy {p}/{a.n}  reported {r}/{a.n}  -> {fn}")

if __name__ == "__main__": asyncio.run(main())
