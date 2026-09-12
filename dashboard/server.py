"""Read-only local dashboard for peer-forensics experiments.
Reads pilot/results/** and logs/*.txt. Never writes anything. Usage: python3 server.py [port]"""
import json, os, sys, glob, html
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS = os.path.join(ROOT, "pilot", "results")
LOGS = os.path.join(ROOT, "logs")

def safe(base, rel):
    p = os.path.abspath(os.path.join(base, rel))
    if not p.startswith(base + os.sep) and p != base: raise PermissionError(rel)
    return p

def jload(p, default=None):
    try: return json.load(open(p))
    except Exception: return default

def experiments():
    out = []
    for d in sorted(glob.glob(os.path.join(RESULTS, "*"))):
        if not os.path.isdir(d): continue
        name = os.path.basename(d)
        if os.path.exists(os.path.join(d, "_manifest.json")): kind = "pilot"
        elif glob.glob(os.path.join(d, "*", "meta.json")): kind = "resample"
        else: kind = "other"
        out.append(dict(name=name, kind=kind, mtime=max([os.path.getmtime(d)] + [os.path.getmtime(f) for f in glob.glob(os.path.join(d, "**", "run.json"), recursive=True)])))
    return out

def pilot_view(name):
    d = safe(RESULTS, name); man = jload(os.path.join(d, "_manifest.json"), {})
    rows, counts = [], {}
    for c, s in man.get("runs", []):
        rd = os.path.join(d, f"{c}__{s:02d}")
        run = jload(os.path.join(rd, "run.json")); tr_exists = os.path.exists(os.path.join(rd, "transcript.json"))
        status = "done" if run else ("partial" if os.path.isdir(rd) else "pending")
        row = dict(run=f"{c}__{s:02d}", condition=c, status=status, path=f"{name}/{c}__{s:02d}")
        if run:
            row.update(end=run["end_reason"], forbidden=run["n_forbidden"], score=run["score"], valid=run["valid_csv"], op=run["n_operator_msgs"],
                       brief_turn=run["brief_read_turn"], exposed=run["exposed_before_first_decision"], tokens=run["usage"]["prompt_tokens"] + run["usage"]["completion_tokens"])
            cc = counts.setdefault(c, dict(scheduled=0, done=0, forbidden=0, op=0))
            cc["done"] += 1; cc["forbidden"] += int(run["n_forbidden"] > 0); cc["op"] += int(run["n_operator_msgs"] > 0)
        counts.setdefault(c, dict(scheduled=0, done=0, forbidden=0, op=0))["scheduled"] += 1
        rows.append(row)
    cfg = man.get("config", {})
    return dict(kind="pilot", name=name, model=cfg.get("model"), provider=cfg.get("provider"), effort=cfg.get("effort"), created=man.get("created"),
                conditions=cfg.get("conditions", {}), rows=rows, counts=counts)

def resample_view(name):
    d = safe(RESULTS, name); groups = []
    for g in sorted(glob.glob(os.path.join(d, "*", "meta.json"))):
        gd = os.path.dirname(g); meta = jload(g, {}); gname = os.path.basename(gd)
        samples = []
        for sd in sorted(glob.glob(os.path.join(gd, "sample-*"))):
            run = jload(os.path.join(sd, "run.json")); db = jload(os.path.join(sd, "debrief.json"))
            samples.append(dict(sample=os.path.basename(sd), path=f"{name}/{gname}/{os.path.basename(sd)}", status="done" if run else "running",
                                end=run and run["end_reason"], forbidden=run and run["n_forbidden"], score=run and run["score"], op=run and run["n_operator_msgs"],
                                debrief=(db or {}).get("answer")))
        done = [s for s in samples if s["status"] == "done" and s["end"] in ("submitted", "final_reply_without_submit")]
        groups.append(dict(group=gname, source=meta.get("source_run"), source_condition=meta.get("source_condition"), target=meta.get("target_condition"),
                           branch_turn=meta.get("branch_turn"), n=meta.get("n"), warnings=meta.get("warnings", []), samples=samples,
                           done=len(done), forbidden=sum(s["forbidden"] > 0 for s in done), op=sum(s["op"] > 0 for s in done)))
    return dict(kind="resample", name=name, groups=groups)

def transcript_view(rel):
    rd = safe(RESULTS, rel)
    t = jload(os.path.join(rd, "transcript.json")); g = jload(os.path.join(rd, "grade.json"), {}); db = jload(os.path.join(rd, "debrief.json"))
    if t is None:
        cps = sorted(glob.glob(os.path.join(rd, "step-*.json")))
        if cps:
            cp = jload(cps[-1], {}); return dict(partial=True, steps=[cp.get("step")], last_turn=cp.get("turn"))
        return dict(missing=True)
    return dict(condition=t.get("condition"), end=t.get("end_reason"), error=t.get("error"), steps=t.get("steps", []), actions=t.get("actions", {}),
                grade=g.get("grade"), debrief=db, initial_brief=(jload(os.path.join(rd, "setup.json"), {}).get("initial_fs", {}) or {}).get("/workspace/brief.txt"))

def log_tail(name, n=200):
    p = safe(LOGS, name)
    try:
        lines = open(p, errors="replace").read().splitlines()
        return dict(name=name, lines=lines[-n:], total=len(lines), mtime=os.path.getmtime(p))
    except FileNotFoundError:
        return dict(name=name, lines=[], total=0)

INDEX = open(os.path.join(os.path.dirname(__file__), "index.html")).read()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/":
                b = INDEX.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            elif u.path == "/api/experiments": self.send_json(dict(experiments=experiments(), logs=sorted(os.path.basename(f) for f in glob.glob(os.path.join(LOGS, "*.txt")))))
            elif u.path == "/api/experiment":
                k = q.get("kind"); self.send_json(pilot_view(q["name"]) if k == "pilot" else resample_view(q["name"]))
            elif u.path == "/api/transcript": self.send_json(transcript_view(q["path"]))
            elif u.path == "/api/log": self.send_json(log_tail(q["name"], int(q.get("n", 200))))
            elif u.path == "/api/notes":
                try: txt = open(os.path.join(ROOT, "EXPERIMENT_LOG.md")).read()
                except FileNotFoundError: txt = ""
                self.send_json(dict(text=txt))
            else: self.send_json(dict(error="not found"), 404)
        except PermissionError: self.send_json(dict(error="forbidden"), 403)
        except Exception as e: self.send_json(dict(error=repr(e)), 500)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"dashboard: http://localhost:{port}  (reads {RESULTS} and {LOGS}; read-only)")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
