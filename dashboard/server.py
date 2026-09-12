"""Read-only local dashboard for peer-forensics experiments.
Reads pilot/results/** , logs/*.txt and EXPERIMENT_LOG.md. Never writes. Usage: python3 server.py [port]"""
import glob, json, os, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from stats import fisher_two_sided, rate

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS = os.path.join(ROOT, "pilot", "results")
LOGS = os.path.join(ROOT, "logs")
EXPERIMENT_LOG = os.path.join(ROOT, "EXPERIMENT_LOG.md")
COMPLETE_ENDINGS = ("submitted", "final_reply_without_submit")

# ---------------------------------------------------------------- helpers
def safe_path(base, rel):
    """Resolve rel under base; refuse anything that escapes."""
    p = os.path.abspath(os.path.join(base, rel))
    if p != base and not p.startswith(base + os.sep): raise PermissionError(rel)
    return p

def load_json(path, default=None):
    try:
        with open(path) as f: return json.load(f)
    except (OSError, ValueError): return default

def read_text(path):
    try:
        with open(path, errors="replace") as f: return f.read()
    except OSError: return ""

def condition_description(brief_text):
    """One-line description of a brief variant: what is appended after the common source notes."""
    m = re.search(r"\nAuthor: (.*)\n(Suggested next step: .*)\n?$", brief_text)
    if not m: return "source notes only: route exists, previous job used it, its spreadsheet was checked 5/5 correct. No author, no recommendation."
    return f"source notes + author line \"{m.group(1)}\" + \"{m.group(2)}\""

def log_entry(name):
    """Section of EXPERIMENT_LOG.md whose heading starts with the experiment name."""
    for sec in read_text(EXPERIMENT_LOG).split("\n## "):
        if sec.startswith(name): return "## " + sec.strip()
    return ""

# ---------------------------------------------------------------- experiment discovery
def experiment_kind(d):
    if os.path.exists(os.path.join(d, "_manifest.json")): return "pilot"
    if glob.glob(os.path.join(d, "*", "meta.json")): return "resample"
    return "other"

def list_experiments():
    out = []
    for d in sorted(glob.glob(os.path.join(RESULTS, "*"))):
        if not os.path.isdir(d): continue
        stamps = [os.path.getmtime(d)] + [os.path.getmtime(f) for f in glob.glob(os.path.join(d, "**", "run.json"), recursive=True)]
        out.append(dict(name=os.path.basename(d), kind=experiment_kind(d), mtime=max(stamps)))
    return out

# ---------------------------------------------------------------- pilot view
def pilot_run_row(exp_name, rdir, condition, seed):
    run = load_json(os.path.join(rdir, "run.json"))
    row = dict(run=f"{condition}__{seed:02d}", path=f"{exp_name}/{condition}__{seed:02d}",
               status="done" if run else ("partial" if os.path.isdir(rdir) else "pending"))
    if run:
        row.update(end=run["end_reason"], forbidden=run["n_forbidden"], score=run["score"], valid=run["valid_csv"],
                   op=run["n_operator_msgs"], brief_turn=run["brief_read_turn"], exposed=run["exposed_before_first_decision"],
                   tokens=run["usage"]["prompt_tokens"] + run["usage"]["completion_tokens"])
    return row

def pilot_view(name):
    d = safe_path(RESULTS, name)
    man = load_json(os.path.join(d, "_manifest.json"), {})
    cfg = man.get("config", {})
    by_cond = {}
    for c, s in man.get("runs", []):
        by_cond.setdefault(c, []).append(pilot_run_row(name, os.path.join(d, f"{c}__{s:02d}"), c, s))
    conditions = []
    for c, rows in sorted(by_cond.items()):
        done = [r for r in rows if r["status"] == "done"]
        complete = [r for r in done if r["end"] in COMPLETE_ENDINGS]
        conditions.append(dict(
            condition=c, description=condition_description(cfg.get("conditions", {}).get(c, "")),
            brief=cfg.get("conditions", {}).get(c, ""), rows=rows,
            stats=dict(scheduled=len(rows), done=len(done), complete=len(complete),
                       forbidden=rate(sum(r["forbidden"] > 0 for r in complete), len(complete)),
                       operator=rate(sum(r["op"] > 0 for r in complete), len(complete)),
                       mean_score=(sum(r["score"] or 0 for r in complete) / len(complete)) if complete else None,
                       valid_csv=sum(bool(r["valid"]) for r in complete),
                       other_endings=[r["end"] for r in done if r["end"] not in COMPLETE_ENDINGS])))
    # pairwise Fisher tests on forbidden-route counts
    comparisons = []
    for i in range(len(conditions)):
        for k in range(i + 1, len(conditions)):
            x, y = conditions[i]["stats"]["forbidden"], conditions[k]["stats"]["forbidden"]
            comparisons.append(dict(a=conditions[i]["condition"], b=conditions[k]["condition"],
                                    p=fisher_two_sided(x["k"], x["n"] - x["k"], y["k"], y["n"] - y["k"])))
    return dict(kind="pilot", name=name, model=cfg.get("model"), provider=cfg.get("provider"), effort=cfg.get("effort"),
                temperature=cfg.get("temperature"), created=man.get("created"), conditions=conditions, comparisons=comparisons,
                notes=log_entry(name))

# ---------------------------------------------------------------- resample view
def resample_sample_row(exp_name, gname, sdir):
    run = load_json(os.path.join(sdir, "run.json")); db = load_json(os.path.join(sdir, "debrief.json"), {})
    return dict(sample=os.path.basename(sdir), path=f"{exp_name}/{gname}/{os.path.basename(sdir)}",
                status="done" if run else "running", end=run and run["end_reason"], forbidden=run and run["n_forbidden"],
                score=run and run["score"], op=run and run["n_operator_msgs"], debrief=db.get("answer"), debrief2=db.get("answer2"))

def resample_group(exp_name, gdir):
    meta = load_json(os.path.join(gdir, "meta.json"), {}); gname = os.path.basename(gdir)
    samples = [resample_sample_row(exp_name, gname, sd) for sd in sorted(glob.glob(os.path.join(gdir, "sample-*")))]
    complete = [s for s in samples if s["status"] == "done" and s["end"] in COMPLETE_ENDINGS]
    return dict(group=gname, source=meta.get("source_run"), source_condition=meta.get("source_condition"),
                target=meta.get("target_condition"), branch_turn=meta.get("branch_turn"), n=meta.get("n"),
                warnings=meta.get("warnings", []), samples=samples,
                stats=dict(complete=len(complete), forbidden=rate(sum(s["forbidden"] > 0 for s in complete), len(complete)),
                           operator=rate(sum(s["op"] > 0 for s in complete), len(complete)),
                           debriefs=sum(bool(s["debrief"]) for s in samples), debriefs2=sum(bool(s["debrief2"]) for s in samples)))

def resample_pairs(groups):
    """For each source run, compare its groups pairwise (e.g. continued as C vs as B) with Fisher's exact test."""
    by_source = {}
    for g in groups: by_source.setdefault((g["source"], g["branch_turn"]), []).append(g)
    pairs = []
    for (src, bt), gs in sorted(by_source.items()):
        gs = sorted(gs, key=lambda g: g["target"], reverse=True)
        for i in range(len(gs)):
            for k in range(i + 1, len(gs)):
                x, y = gs[i]["stats"]["forbidden"], gs[k]["stats"]["forbidden"]
                pairs.append(dict(source=src, branch_turn=bt, a=gs[i]["target"], a_rate=x, b=gs[k]["target"], b_rate=y,
                                  p=fisher_two_sided(x["k"], x["n"] - x["k"], y["k"], y["n"] - y["k"])))
    return pairs

def resample_view(name):
    d = safe_path(RESULTS, name)
    groups = [resample_group(name, os.path.dirname(m)) for m in sorted(glob.glob(os.path.join(d, "*", "meta.json")))]
    pooled = {}
    for g in groups:
        t = pooled.setdefault(g["target"], [0, 0]); t[0] += g["stats"]["forbidden"]["k"]; t[1] += g["stats"]["forbidden"]["n"]
    return dict(kind="resample", name=name, groups=groups, pairs=resample_pairs(groups),
                pooled={t: rate(k, n) for t, (k, n) in sorted(pooled.items())}, notes=log_entry(name))

# ---------------------------------------------------------------- transcript + logs
def prefix_steps(messages):
    """Turn a frozen message prefix (from a resample group's meta.json) into step records so the
    detail view can show the turns that were held fixed before the branch point."""
    steps, turn, pending = [], -1, {}
    for m in messages[2:]:
        if m["role"] == "assistant":
            turn += 1
            calls = m.get("tool_calls") or []
            pending = {tc["id"]: tc for tc in calls}
            steps.append(dict(turn=turn, frozen=True, reasoning=m.get("reasoning"), content=m.get("content"), not_executed=[],
                              tool_calls=[dict(id=tc["id"], name=tc["function"]["name"],
                                               args=load_json_str(tc["function"]["arguments"]), result="") for tc in calls]))
        elif m["role"] == "tool" and steps:
            for tc in steps[-1]["tool_calls"]:
                if tc["id"] == m["tool_call_id"]: tc["result"] = m["content"]
    return steps

def load_json_str(s):
    try: return json.loads(s or "{}")
    except ValueError: return {"_unparsed": s}

def transcript_view(rel):
    rd = safe_path(RESULTS, rel)
    t = load_json(os.path.join(rd, "transcript.json"))
    meta = load_json(os.path.join(os.path.dirname(rd), "meta.json"))          # present only for resample samples
    frozen = prefix_steps(meta["prefix_messages"]) if meta else []
    if t is None:
        cps = sorted(glob.glob(os.path.join(rd, "step-*.json")))
        if not cps: return dict(missing=True)
        cp = load_json(cps[-1], {}); return dict(partial=True, steps=[cp.get("step")], last_turn=cp.get("turn"))
    setup = load_json(os.path.join(rd, "setup.json"), {})
    brief = (setup.get("initial_fs") or {}).get("/workspace/brief.txt")
    if meta and not brief:                                                    # resample sample: brief is in the frozen prefix
        brief = next((tc["result"] for st in frozen for tc in st["tool_calls"] if tc["args"].get("path") == "/workspace/brief.txt"), None)
    return dict(condition=t.get("condition") or (meta or {}).get("target_condition"), end=t.get("end_reason"), error=t.get("error"),
                steps=frozen + t.get("steps", []), branch_turn=(meta or {}).get("branch_turn"),
                actions=t.get("actions", {}), grade=load_json(os.path.join(rd, "grade.json"), {}).get("grade"),
                debrief=load_json(os.path.join(rd, "debrief.json")), initial_brief=brief)

def log_tail(name, n=300):
    lines = read_text(safe_path(LOGS, name)).splitlines()
    return dict(name=name, lines=lines[-n:], total=len(lines))

# ---------------------------------------------------------------- http
INDEX_HTML = read_text(os.path.join(os.path.dirname(__file__), "index.html"))

ROUTES = {
    "/api/experiments": lambda q: dict(experiments=list_experiments(), logs=sorted(os.path.basename(f) for f in glob.glob(os.path.join(LOGS, "*.txt")))),
    "/api/experiment": lambda q: pilot_view(q["name"]) if q.get("kind") == "pilot" else resample_view(q["name"]),
    "/api/transcript": lambda q: transcript_view(q["path"]),
    "/api/log": lambda q: log_tail(q["name"], int(q.get("n", 300))),
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, ctype, code=200):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/": return self._send(INDEX_HTML.encode(), "text/html; charset=utf-8")
        handler = ROUTES.get(u.path)
        if handler is None: return self._send(b'{"error":"not found"}', "application/json", 404)
        try: self._send(json.dumps(handler(q)).encode(), "application/json")
        except PermissionError: self._send(b'{"error":"forbidden"}', "application/json", 403)
        except Exception as e: self._send(json.dumps(dict(error=repr(e))).encode(), "application/json", 500)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"dashboard: http://localhost:{port}  (read-only view of {RESULTS} and {LOGS})")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
