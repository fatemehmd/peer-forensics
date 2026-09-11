"""Run rollouts: models x conditions x n. Saves one JSON per rollout in results/.
Usage: OPENROUTER_API_KEY=... python run.py --models openai/gpt-oss-120b --conditions peers_doing solo_info --n 20
       python run.py --list-models qwen   # find exact model ids on OpenRouter"""
import argparse, asyncio, json, os, sys, time, uuid, random
from openai import AsyncOpenAI
import env as E

MAX_TURNS = 30

async def rollout(client, model, condition, seed, sem, outdir, reasoning_effort):
    async with sem:
        env = E.Env(condition)
        msgs = [{"role": "system", "content": E.SYSTEM_PROMPT}, {"role": "user", "content": env.initial_user_message()}]
        transcript = []  # assistant reasoning/content + tool calls in order
        err = None
        for turn in range(MAX_TURNS):
            try:
                r = await client.chat.completions.create(
                    model=model, messages=msgs, tools=E.TOOLS, temperature=1.0,
                    extra_body={"reasoning": {"effort": reasoning_effort}})
            except Exception as e:
                err = repr(e); break
            m = r.choices[0].message
            reasoning = getattr(m, "reasoning", None) or (m.model_extra or {}).get("reasoning")
            rd = (m.model_extra or {}).get("reasoning_details")
            entry = dict(turn=turn, reasoning=reasoning, content=m.content, tool_calls=[])
            am = {"role": "assistant", "content": m.content or ""}
            if reasoning: am["reasoning"] = reasoning
            if rd: am["reasoning_details"] = rd
            if m.tool_calls:
                am["tool_calls"] = [tc.model_dump() for tc in m.tool_calls]
            msgs.append(am)
            if not m.tool_calls:
                transcript.append(entry); break
            for tc in m.tool_calls:
                try: args = json.loads(tc.function.arguments or "{}")
                except Exception: args = {"_raw": tc.function.arguments}
                out = env.call(tc.function.name, args)
                entry["tool_calls"].append(dict(name=tc.function.name, args=args, result=out[:500]))
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": out})
            transcript.append(entry)
            if env.done: break
        rec = dict(id=str(uuid.uuid4())[:8], model=model, condition=condition, seed=seed, error=err,
                   turns=len(transcript), metrics=env.metrics, transcript=transcript, tool_log=env.log)
        fn = f"{outdir}/{model.replace('/','_')}__{condition}__{seed}.json"
        json.dump(rec, open(fn, "w"), indent=1)
        mm = env.metrics
        print(f"[{condition:20s} {model:28s} s{seed:02d}] proxy={int(mm['used_proxy'])} report={int(mm['reported'])} post={int(mm['posted'])} rows={mm['rows_filled']} turns={len(transcript)} {('ERR '+err[:80]) if err else ''}", flush=True)
        return rec

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["openai/gpt-oss-120b"])
    ap.add_argument("--conditions", nargs="+", default=list(E.CONDITIONS))
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--list-models", default=None)
    a = ap.parse_args()
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    if a.list_models:
        ms = await client.models.list()
        for m in ms.data:
            if a.list_models.lower() in m.id.lower(): print(m.id)
        return
    os.makedirs(a.outdir, exist_ok=True)
    sem = asyncio.Semaphore(a.concurrency)
    jobs = []
    for model in a.models:
        for c in a.conditions:
            for s in range(a.n):
                fn = f"{a.outdir}/{model.replace('/','_')}__{c}__{s}.json"
                if os.path.exists(fn): continue   # resumable
                jobs.append(rollout(client, model, c, s, sem, a.outdir, a.effort))
    random.shuffle(jobs)
    print(f"{len(jobs)} rollouts to run", flush=True)
    await asyncio.gather(*jobs)

if __name__ == "__main__":
    asyncio.run(main())
