"""Runs one model against the simulator. No nudges: a plain final reply ends the run.
Usage:
  python harness.py --list qwen                      # find model ids on OpenRouter
  python harness.py --model qwen/... --condition smoke_local --n 1 --out results/smoke
  python harness.py --model qwen/... --pilot --n 8 --out results/pilot_v1
"""
import argparse, asyncio, json, os, random, time
from openai import AsyncOpenAI

def load_env():
    """Read KEY=value lines from ../.env (gitignored) so no shell export is needed."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()
from sim import Sim, SYSTEM_PROMPT, USER_MESSAGE, TOOLS

MAX_TURNS = 30

async def run_one(client, model, condition, seed, out, effort, provider, sem):
    async with sem:
        sim = Sim(condition)
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": USER_MESSAGE}]
        steps, usage, end = [], dict(prompt_tokens=0, completion_tokens=0), None
        extra = {"reasoning": {"effort": effort}}
        if provider: extra["provider"] = {"order": [provider], "allow_fallbacks": False}
        t0 = time.time()
        for turn in range(MAX_TURNS):
            try:
                r = await client.chat.completions.create(model=model, messages=msgs, tools=TOOLS, temperature=1.0, max_tokens=6000, extra_body=extra)
            except Exception as e:
                end = f"api_error: {e!r}"[:300]; break
            if r.usage:
                usage["prompt_tokens"] += r.usage.prompt_tokens or 0; usage["completion_tokens"] += r.usage.completion_tokens or 0
            m = r.choices[0].message
            ex = m.model_extra or {}
            reasoning = getattr(m, "reasoning", None) or ex.get("reasoning")
            step = dict(turn=turn, reasoning=reasoning, content=m.content, tool_calls=[], provider=getattr(r, "provider", None) or ex.get("provider"))
            am = {"role": "assistant", "content": m.content or ""}
            if reasoning: am["reasoning"] = reasoning
            if ex.get("reasoning_details"): am["reasoning_details"] = ex["reasoning_details"]
            if m.tool_calls: am["tool_calls"] = [tc.model_dump() for tc in m.tool_calls]
            msgs.append(am)
            if not m.tool_calls:
                steps.append(step); end = "final_reply_without_submit"; break
            for tc in m.tool_calls:
                try: args = json.loads(tc.function.arguments or "{}")
                except Exception: args = {"_unparsed": tc.function.arguments}
                res = sim.call(tc.function.name, args)
                step["tool_calls"].append(dict(name=tc.function.name, args=args, result=res))
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": res})
            steps.append(step)
            if sim.done: end = "submitted"; break
        else:
            end = "turn_limit"
        rec = dict(model=model, provider_requested=provider, effort=effort, temperature=1.0, max_turns=MAX_TURNS,
                   condition=condition, seed=seed, end_reason=end, seconds=round(time.time() - t0, 1), usage=usage,
                   n_steps=len(steps), reasoning_returned=any(s["reasoning"] for s in steps),
                   sim=sim.record(), steps=steps, tool_log=sim.log, messages=msgs)
        os.makedirs(out, exist_ok=True)
        json.dump(rec, open(f"{out}/{condition}__{seed:02d}.json", "w"), indent=1)
        sr = rec["sim"]
        print(f"[{condition} s{seed:02d}] end={end:28s} forbidden={len(sr['forbidden_attempts'])} score={sr['scoring']['score']} "
              f"reports={len(sr['reports_accessed'])} op_msgs={len(sr['operator_msgs'])} brief={int(sr['read_brief'])} "
              f"reasoning={int(rec['reasoning_returned'])} tok={usage['prompt_tokens']}+{usage['completion_tokens']}", flush=True)
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
    conds = ["A", "B", "C"] if a.pilot else [a.condition]
    jobs = [(c, s) for c in conds for s in range(a.n) if not os.path.exists(f"{a.out}/{c}__{s:02d}.json")]
    random.seed(0); random.shuffle(jobs)
    print(f"{len(jobs)} runs scheduled -> {a.out}", flush=True)
    sem = asyncio.Semaphore(a.concurrency)
    await asyncio.gather(*[run_one(client, a.model, c, s, a.out, a.effort, a.provider, sem) for c, s in jobs])

if __name__ == "__main__": asyncio.run(main())
