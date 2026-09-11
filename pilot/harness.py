"""Runs one model against the simulator. No nudges: a plain final reply ends the run.
Stops immediately at submit; truncated replies are recorded as token_limit and their tool calls are NOT executed.
A manifest of every scheduled run is written first; every scheduled run produces a result file, even on error.
Usage:
  python harness.py --list qwen
  python harness.py --model qwen/qwen3.6-27b --provider alibaba --condition smoke_local --n 1 --out results/smoke
  python harness.py --model qwen/qwen3.6-27b --provider alibaba --pilot --n 10 --out results/pilot_v1
"""
import argparse, asyncio, json, os, random, time, traceback
from openai import AsyncOpenAI
from sim import Sim, SYSTEM_PROMPT, USER_MESSAGE, TOOLS

MAX_TURNS = 30
MAX_TOKENS = 6000

def load_env():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()

def step_loop_sync(sim, turn, m, finish_reason, msgs):
    """Apply one model reply to the simulator. Returns (step, end_reason or None)."""
    ex = m.model_extra or {}
    reasoning = getattr(m, "reasoning", None) or ex.get("reasoning")
    step = dict(turn=turn, finish_reason=finish_reason, reasoning=reasoning, content=m.content, tool_calls=[], not_executed=[])
    am = {"role": "assistant", "content": m.content or ""}
    if reasoning: am["reasoning"] = reasoning
    if ex.get("reasoning_details"): am["reasoning_details"] = ex["reasoning_details"]
    if m.tool_calls: am["tool_calls"] = [tc.model_dump() for tc in m.tool_calls]
    msgs.append(am)
    if finish_reason == "length":
        step["not_executed"] = [tc.function.name for tc in (m.tool_calls or [])]
        return step, "token_limit"
    if not m.tool_calls:
        return step, "final_reply_without_submit"
    sim.begin_turn(turn)
    for i, tc in enumerate(m.tool_calls):
        if sim.done:                                            # stop immediately at submit
            step["not_executed"].append(tc.function.name)
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": "ERROR: task already submitted"})
            continue
        try: args = json.loads(tc.function.arguments or "{}")
        except Exception: args = {"_unparsed": tc.function.arguments}
        res = sim.call(tc.function.name, args)
        step["tool_calls"].append(dict(name=tc.function.name, args=args, result=res))
        msgs.append({"role": "tool", "tool_call_id": tc.id, "content": res})
    return step, ("submitted" if sim.done else None)

async def run_one(client, model, condition, seed, out, effort, provider, sem):
    async with sem:
        sim = Sim(condition)
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": USER_MESSAGE}]
        steps, usage, end, err = [], dict(prompt_tokens=0, completion_tokens=0), None, None
        extra = {"reasoning": {"effort": effort}}
        if provider: extra["provider"] = {"order": [provider], "allow_fallbacks": False}
        t0 = time.time()
        try:
            for turn in range(MAX_TURNS):
                try:
                    r = await client.chat.completions.create(model=model, messages=msgs, tools=TOOLS, temperature=1.0,
                                                             max_tokens=MAX_TOKENS, extra_body=extra)
                except Exception as e:
                    end, err = "api_error", repr(e)[:500]; break
                if r.usage:
                    usage["prompt_tokens"] += r.usage.prompt_tokens or 0; usage["completion_tokens"] += r.usage.completion_tokens or 0
                ch = r.choices[0]
                step, end = step_loop_sync(sim, turn, ch.message, ch.finish_reason, msgs)
                step["provider"] = getattr(r, "provider", None) or (r.model_extra or {}).get("provider")
                steps.append(step)
                if end: break
            else:
                end = "turn_limit"
        except Exception as e:                                  # harness bug: still write a record
            end, err = "harness_error", traceback.format_exc()[-1500:]
        rec = dict(model=model, provider_requested=provider, effort=effort, temperature=1.0, max_turns=MAX_TURNS, max_tokens=MAX_TOKENS,
                   condition=condition, seed=seed, end_reason=end, error=err, seconds=round(time.time() - t0, 1), usage=usage,
                   n_steps=len(steps), reasoning_returned=any(s["reasoning"] for s in steps),
                   sim=sim.record(), steps=steps, tool_log=sim.log, messages=msgs)
        json.dump(rec, open(f"{out}/{condition}__{seed:02d}.json", "w"), indent=1)
        sr = rec["sim"]
        print(f"[{condition} s{seed:02d}] end={end:26s} forbidden={len(sr['forbidden_attempts'])} score={sr['scoring']['score']} "
              f"delivered={len(sr['reports_delivered'])} op_msgs={len(sr['operator_msgs'])} brief_turn={sr['brief_read_turn']} "
              f"reasoning={int(rec['reasoning_returned'])} tok={usage['prompt_tokens']}+{usage['completion_tokens']}"
              f"{'  ERR ' + err[:100] if err else ''}", flush=True)
        return rec

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model"); ap.add_argument("--condition"); ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--n", type=int, default=1); ap.add_argument("--out", default="results/tmp")
    ap.add_argument("--effort", default="medium"); ap.add_argument("--provider", default=None)
    ap.add_argument("--concurrency", type=int, default=8); ap.add_argument("--list", default=None)
    a = ap.parse_args()
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    if a.list:
        for m in (await client.models.list()).data:
            if a.list.lower() in m.id.lower(): print(m.id)
        return
    os.makedirs(a.out, exist_ok=True)
    conds = ["A", "B", "C"] if a.pilot else [a.condition]
    scheduled = [(c, s) for c in conds for s in range(a.n)]
    mpath = f"{a.out}/_manifest.json"
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else dict(model=a.model, provider=a.provider, effort=a.effort, runs=[])
    manifest["runs"] = sorted(set(map(tuple, manifest["runs"])) | set(scheduled))
    json.dump(manifest, open(mpath, "w"), indent=1)
    jobs = [(c, s) for c, s in scheduled if not os.path.exists(f"{a.out}/{c}__{s:02d}.json")]
    random.seed(0); random.shuffle(jobs)
    print(f"{len(jobs)} runs to do of {len(scheduled)} scheduled -> {a.out}", flush=True)
    sem = asyncio.Semaphore(a.concurrency)
    results = await asyncio.gather(*[run_one(client, a.model, c, s, a.out, a.effort, a.provider, sem) for c, s in jobs], return_exceptions=True)
    for (c, s), r in zip(jobs, results):
        if isinstance(r, Exception): print(f"[{c} s{s:02d}] UNHANDLED {r!r}", flush=True)

if __name__ == "__main__": asyncio.run(main())
