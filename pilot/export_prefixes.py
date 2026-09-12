"""Export the exact conversation up to (and including) the decision turn for chosen runs, for internals work.
Writes <out>/<model>/<cell>/<run>__<route|honest>.json with: the messages the model saw before its decision reply,
the decision reply itself (reasoning + content + tool calls), and pointers. Also writes an index with matched
cheater/honest sets per cell.

Usage: python export_prefixes.py --out ../internals/prefixes
"""
import argparse, glob, json, os

CELLS = {  # folder -> (model tag, conditions)
    "pressure_v1":            ("qwen3.6-27b",      ["M", "MH", "MP", "MHP"]),
    "pressure_costly_v1":     ("qwen3.6-27b",      ["MHP_costly"]),
    "excite_v1":              ("qwen3.6-27b",      ["ME", "MHE"]),
    "pilot_v2":               ("qwen3.6-27b",      ["A", "B", "C"]),
    "pilot_v3_original":      ("qwen3.6-27b",      ["B", "C"]),
    "pressure_v1_q122b":      ("qwen3.5-122b-a10b", ["M", "MH", "MP", "MHP"]),
    "pressure_costly_v1_q122b": ("qwen3.5-122b-a10b", ["MHP_costly"]),
    "excite_v1_q122b":        ("qwen3.5-122b-a10b", ["ME", "MHE"]),
    "pilot_v2_q122b":         ("qwen3.5-122b-a10b", ["A", "B", "C"]),
}

def decision_turn(t):
    """First turn with a decision action: cache-route fetch, direct fetch, spreadsheet write, operator message, or submit."""
    for st in t["steps"]:
        for c in st["tool_calls"]:
            if c["name"] in ("http_get", "report_to_operator", "submit") or (c["name"] == "write_file" and c["args"].get("path") == "/workspace/revenue.csv"):
                return st["turn"]
    return None

def messages_before_turn(t, turn):
    """Messages as sent to the API for the request that produced `turn` (system, user, then completed turns < turn)."""
    msgs, k = [], -1
    for m in t["messages"]:
        if m["role"] == "assistant":
            k += 1
            if k >= turn: break
        elif m["role"] == "tool" and k >= turn: break
        msgs.append(m)
    return msgs

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="../internals/prefixes"); a = ap.parse_args()
    index = {}
    for folder, (model, conds) in CELLS.items():
        for f in sorted(glob.glob(f"results/{folder}/*/transcript.json")):
            if ".rate-limited-" in f or ".partial-" in f: continue
            t = json.load(open(f)); cond = t.get("condition"); run = f.split("/")[2]
            if cond not in conds: continue
            dt = decision_turn(t)
            if dt is None: continue
            a_ = t["actions"]; route = a_["n_forbidden_attempts"] > 0
            step = next(s for s in t["steps"] if s["turn"] == dt)
            rec = dict(model=model, folder=folder, run=run, condition=cond, outcome="route" if route else "honest", decision_turn=dt,
                       system_prompt=t["messages"][0]["content"], user_message=t["messages"][1]["content"],
                       messages_before_decision=messages_before_turn(t, dt),
                       decision_reply=dict(reasoning=step["reasoning"], content=step["content"], tool_calls=[dict(name=c["name"], args=c["args"]) for c in step["tool_calls"]]),
                       source=f)
            od = os.path.join(a.out, model, f"{folder}__{cond}"); os.makedirs(od, exist_ok=True)
            with open(os.path.join(od, f"{run}__{rec['outcome']}.json"), "w") as fh: json.dump(rec, fh, indent=1)
            index.setdefault(model, {}).setdefault(f"{folder}__{cond}", {"route": [], "honest": []})[rec["outcome"]].append(run)
    os.makedirs(a.out, exist_ok=True)
    json.dump(index, open(os.path.join(a.out, "index.json"), "w"), indent=1)
    for model, cells in index.items():
        print(model)
        for cell, d in cells.items(): print(f"  {cell:34s} route {len(d['route']):>2}  honest {len(d['honest']):>2}")

if __name__ == "__main__": main()
