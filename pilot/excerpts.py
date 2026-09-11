"""Print the full reasoning + actions around the decision point for chosen runs. Usage: python excerpts.py results/pilot_v1 A_00 B_00 ..."""
import json, sys
d = sys.argv[1]
for name in sys.argv[2:]:
    c, s = name.split("_"); r = json.load(open(f"{d}/{c}__{int(s):02d}.json"))
    print(f"\n{'='*30} {name}  end={r['end_reason']} forbidden={r['sim']['forbidden_attempts']} score={r['sim']['scoring']['score']}")
    for st in r["steps"]:
        print(f"\n--- turn {st['turn']} ---")
        if st["reasoning"]: print("[reasoning]", st["reasoning"].strip())
        if st["content"]: print("[content]", st["content"].strip())
        for tc in st["tool_calls"]:
            a = tc["args"]; short = {k: (v[:80] + "…" if isinstance(v, str) and len(v) > 80 else v) for k, v in a.items()}
            print(f"[call] {tc['name']}({short}) -> {tc['result'][:120]!r}")
    print(f"\n[operator msgs] {r['sim']['operator_msgs']}\n[submit note] {r['sim']['submit_note']}")
