"""Full reasoning + actions for chosen runs. Usage: python excerpts.py results/pilot_v2 A_00 B_00 C_00"""
import json, sys, os
d = sys.argv[1]
for name in sys.argv[2:]:
    c, s = name.rsplit("_", 1); rd = os.path.join(d, f"{c}__{int(s):02d}")
    t = json.load(open(os.path.join(rd, "transcript.json"))); g = json.load(open(os.path.join(rd, "grade.json"))).get("grade") or {}
    a = t["actions"]
    print(f"\n{'='*30} {name}  end={t['end_reason']} forbidden={[f['url'] for f in a['forbidden_attempts']]} score={g.get('score')} valid={g.get('valid_csv')} {g.get('problems')}")
    for st in t["steps"]:
        print(f"\n--- turn {st['turn']} ---")
        if st.get("finish_reason") == "length": print("[TRUNCATED: token limit]")
        if st["reasoning"]: print("[reasoning]", st["reasoning"].strip())
        if st["content"]: print("[content]", st["content"].strip())
        for tc in st["tool_calls"]:
            ar = {k: (v[:80] + "…" if isinstance(v, str) and len(v) > 80 else v) for k, v in tc["args"].items()}
            print(f"[call] {tc['name']}({ar}) -> {tc['result'][:120]!r}")
        if st["not_executed"]: print(f"[not executed] {st['not_executed']}")
    print(f"\n[brief read turn] {a['brief_read_turn']}  [exposed before first decision] {a['exposed_before_first_decision']}")
    print(f"[operator msgs] {[m['text'] for m in a['operator_msgs']]}\n[submit note] {a['submit_note']}")
