"""Move failed runs (api_error / harness_error / turn_limit) in a folder to <run>.rate-limited-<ts> so the harness refills them.
Nothing is deleted; set-aside runs still count as observed attempts in replication_analyze.py. Prints how many were moved."""
import json, glob, os, sys, time
folder = sys.argv[1]; ts = int(time.time()); moved = 0
for d in glob.glob(f"{folder}/*__*"):
    if not os.path.isdir(d) or ".rate-limited-" in d or ".partial-" in d: continue
    rj = os.path.join(d, "run.json")
    r = json.load(open(rj)) if os.path.exists(rj) else None
    if r and r["end_reason"] in ("submitted", "final_reply_without_submit"): continue
    os.rename(d, f"{d}.rate-limited-{ts}"); moved += 1
print(f"{folder}: set aside {moved}")
