"""Table of every scheduled run + excerpts for hand review. Usage: python analyze.py results/pilot_v1"""
import json, glob, sys, re, os
d = sys.argv[1]
recs = sorted((json.load(open(f)) for f in glob.glob(f"{d}/*.json")), key=lambda r: (r["condition"], r["seed"]))
print(f"{'run':8} {'end':30} {'brief':5} {'forbid':6} {'score':5} {'supp':4} {'op':3} {'reason':6} {'tok_in':7} {'tok_out':7}")
for r in recs:
    s = r["sim"]; sc = s["scoring"]
    print(f"{r['condition']}_{r['seed']:02d}  {r['end_reason'][:30]:30} {int(s['read_brief']):5} {len(s['forbidden_attempts']):6} {sc['score']:5} {sc['correct_and_supported']:4} {len(s['operator_msgs']):3} {int(r['reasoning_returned']):6} {r['usage']['prompt_tokens']:7} {r['usage']['completion_tokens']:7}")
print("\n== counts (runs that read the brief and did not error) ==")
for c in sorted(set(r["condition"] for r in recs)):
    rs = [r for r in recs if r["condition"] == c]
    valid = [r for r in rs if r["sim"]["read_brief"] and not r["end_reason"].startswith("api_error")]
    forb = sum(bool(r["sim"]["forbidden_attempts"]) for r in valid)
    op = sum(bool(r["sim"]["operator_msgs"]) for r in valid)
    print(f"{c}: scheduled {len(rs)}, valid {len(valid)}, attempted forbidden route {forb}/{len(valid)}, sent operator msg {op}/{len(valid)}, "
          f"mean score {sum(r['sim']['scoring']['score'] for r in valid)/max(1,len(valid)):.2f}")
tot_in = sum(r["usage"]["prompt_tokens"] for r in recs); tot_out = sum(r["usage"]["completion_tokens"] for r in recs)
print(f"\ntokens: {tot_in} in, {tot_out} out")
KW = re.compile(r"\b(test|evaluat|experiment|being (watched|graded|assessed)|honeypot|scenario|simulat)", re.I)
print("\n== passages mentioning test/eval words (FOR MANUAL REVIEW, not counted as awareness) ==")
for r in recs:
    for st in r["steps"]:
        for m in KW.finditer(st["reasoning"] or ""):
            t = st["reasoning"]; print(f"  {r['condition']}_{r['seed']:02d} t{st['turn']}: ...{t[max(0,m.start()-80):m.end()+80]!r}...")
