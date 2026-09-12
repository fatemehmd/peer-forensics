"""Sentence-level resampling on the 122B (visible-content deliberation) via assistant prefill on Alibaba.
For each source run that used the route, take the saved decision-turn text, find the pivot sentence
("let me try", "try anyway", "see if it works"), and sample continuations from two prefills of the same turn:
  before  : the text up to the sentence before the pivot
  through : the text through the pivot sentence
The prefix before the decision turn is the saved messages verbatim (as in judgment.py). Continuations run the task to
completion with the original tools; the forbidden-route rate is counted from tool calls. Per-source, paired.

Usage:
  python resample_sentence.py --check
  python resample_sentence.py --run --n 15 --sources results/pressure_v1_q122b --out results/sentence_v1
"""
import argparse, asyncio, glob, json, os, re, time
import harness as H
import judgment as J
from sim import TOOLS

PIVOT = re.compile(r"let me (just )?try|try (it |them )?anyway|see if it works|see what happens|let me attempt", re.I)
SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z`\"'(])")

def sentences(text): return [s for s in SPLIT.split(text.strip()) if s.strip()]

def plan(source_dir):
    t = json.load(open(os.path.join(source_dir, "transcript.json")))
    if not t["actions"]["n_forbidden_attempts"]: return dict(usable=False, reason="source did not use the route")
    b = J.build(source_dir)
    if not b["usable"]: return dict(usable=False, reason=f"prefix checks failed: {b['checks']}")
    bt = b["checks"]["branch_turn"]; dec = next(s for s in t["steps"] if s["turn"] == bt)
    if not any(c["name"] == "http_get" and "cache.internal" in c["args"].get("url", "") for c in dec["tool_calls"]):
        return dict(usable=False, reason="first decision turn is not the cache fetch")
    text = (dec["content"] or "").strip()
    if not text: return dict(usable=False, reason="decision turn has no visible content to prefill")
    sents = sentences(text); pi = next((i for i, s in enumerate(sents) if PIVOT.search(s)), None)
    if pi is None: return dict(usable=False, reason="no pivot sentence found", text=text[:300])
    if pi == 0: return dict(usable=False, reason="pivot is the first sentence; 'before' arm would be empty")
    return dict(usable=True, prefix=b["prefix_messages"], branch_turn=bt, sentences=sents, pivot_index=pi, pivot=sents[pi],
                arms=dict(before=" ".join(sents[:pi]), through=" ".join(sents[:pi + 1])), source_dir=source_dir, condition=b["condition"])

async def continue_prefilled(client, cfg, prefix, sim, start_turn, prefill, outdir, sem):
    msgs = json.loads(json.dumps(prefix)) + [{"role": "assistant", "content": prefill}]
    steps, usage, end, err = [], dict(prompt_tokens=0, completion_tokens=0), None, None
    extra = {"reasoning": {"effort": cfg["effort"]}, "provider": {"order": [cfg["provider"]], "allow_fallbacks": False}}
    os.makedirs(outdir, exist_ok=True)
    try:
        async with sem:
            for turn in range(start_turn, cfg["max_turns"]):
                try:
                    r = await client.chat.completions.create(model=cfg["model"], messages=msgs, tools=TOOLS, temperature=cfg["temperature"], max_tokens=cfg["max_tokens"], extra_body=extra)
                except asyncio.CancelledError: raise
                except Exception as e: end, err = "api_error", repr(e)[:500]; break
                if r.usage: usage["prompt_tokens"] += r.usage.prompt_tokens or 0; usage["completion_tokens"] += r.usage.completion_tokens or 0
                if not getattr(r, "choices", None): end, err = "api_error", "empty response"; break
                ch = r.choices[0]; m = ch.message
                if turn == start_turn:                      # merge the continuation into the prefilled assistant turn
                    msgs.pop(); m.content = prefill + (m.content or "")
                step, end = H.apply_reply(sim, turn, m, ch.finish_reason, msgs)
                if turn == start_turn: step["prefill"] = prefill
                steps.append(step)
                if end: break
            else: end = "turn_limit"
    except asyncio.CancelledError: end, err = "cancelled", "cancelled"
    except Exception as e: end, err = "harness_error", repr(e)[:800]
    rec = dict(end_reason=end, error=err, prefill=prefill, steps=steps, messages=msgs, tool_log=sim.log, actions=sim.summary(), usage=usage)
    H.atomic_write_json(os.path.join(outdir, "transcript.json"), rec); return rec

async def run(a):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"]); sem = asyncio.Semaphore(a.concurrency); jobs = []
    for src_folder in a.sources:
        c = json.load(open(f"{src_folder}/_manifest.json"))["config"]
        cfg = dict(model=c["model"], provider=c["provider"], effort=c["effort"], temperature=c["temperature"], max_turns=c["max_turns"], max_tokens=c["max_tokens"])
        for sd in sorted(glob.glob(f"{src_folder}/MP__*")):
            if not os.path.isdir(sd) or ".rate-limited-" in sd: continue
            p = plan(sd); run_name = os.path.basename(sd); gdir = os.path.join(a.out, run_name); os.makedirs(gdir, exist_ok=True)
            H.atomic_write_json(os.path.join(gdir, "meta.json"), dict(source=sd, usable=p["usable"], reason=p.get("reason"), config=cfg, branch_turn=p.get("branch_turn"),
                                 pivot=p.get("pivot"), pivot_index=p.get("pivot_index"), sentences=p.get("sentences"), arms=p.get("arms"), prefix_messages=p.get("prefix"), created=time.strftime("%H:%M:%S")))
            if not p["usable"]: print(f"skip {run_name}: {p['reason']}"); continue
            for arm, prefill in p["arms"].items():
                for k in range(a.n):
                    od = os.path.join(gdir, f"{arm}-{k:02d}")
                    if os.path.exists(os.path.join(od, "transcript.json")): continue
                    b = J.build(sd); jobs.append(continue_prefilled(client, cfg, b["prefix_messages"], b["sim"], p["branch_turn"], prefill, od, sem))
    print(f"{len(jobs)} continuations -> {a.out}", flush=True)
    res = await asyncio.gather(*jobs, return_exceptions=True)
    for r in res:
        if isinstance(r, Exception): print("UNHANDLED", repr(r)[:200])
    print("ALL DONE", flush=True)

def check(a):
    for src_folder in a.sources:
        for sd in sorted(glob.glob(f"{src_folder}/MP__*")):
            if not os.path.isdir(sd) or ".rate-limited-" in sd: continue
            p = plan(sd); name = os.path.basename(sd)
            if not p["usable"]: print(f"{name}: SKIP ({p['reason']})"); continue
            print(f"{name}: branch turn {p['branch_turn']} | {len(p['sentences'])} sentences, pivot #{p['pivot_index']}: {p['pivot'][:110]!r}")
            print(f"    before : ...{p['arms']['before'][-100:]!r}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--run", action="store_true")
    ap.add_argument("--sources", nargs="+", default=["results/pressure_v1_q122b"]); ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--out", default="results/sentence_v1"); ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args(); check(a) if a.check else (asyncio.run(run(a)) if a.run else ap.print_help())
