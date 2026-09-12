"""Export a static, self-contained copy of the dashboard + docs into docs/ for GitHub Pages.
Reads the same results the live dashboard reads; writes JSON per experiment and a slim JSON per run."""
import glob, json, os, sys, shutil, markdown
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as S
ROOT = S.ROOT; OUT = os.path.join(ROOT, "docs"); DATA = os.path.join(OUT, "data"); RUNS = os.path.join(DATA, "runs")
os.makedirs(RUNS, exist_ok=True)
VIEWS = {"pilot": S.pilot_view, "resample": S.resample_view, "judgment": S.judgment_view, "sentence": S.sentence_view, "commitment": S.commitment_view}

def slim_run(rel):
    t = S.transcript_view(rel)
    if t.get("missing"): return None
    steps = [dict(turn=s.get("turn"), frozen=s.get("frozen", False), finish_reason=s.get("finish_reason"), reasoning=s.get("reasoning"), content=s.get("content"),
                  tool_calls=[dict(name=c["name"], args=c["args"], result=(c["result"] or "")[:400]) for c in (s.get("tool_calls") or [])],
                  not_executed=s.get("not_executed", [])) for s in (t.get("steps") or []) if s]
    a = t.get("actions") or {}
    return dict(condition=t.get("condition"), end=t.get("end"), error=t.get("error"), branch_turn=t.get("branch_turn"), steps=steps,
                actions=dict(forbidden_attempts=a.get("forbidden_attempts"), blocked_direct=a.get("blocked_direct"), operator_msgs=a.get("operator_msgs"),
                             submit_note=a.get("submit_note"), brief_read_turn=a.get("brief_read_turn"), exposed_before_first_decision=a.get("exposed_before_first_decision"),
                             action_log=a.get("action_log")),
                grade=t.get("grade"), debrief=t.get("debrief"), initial_brief=t.get("initial_brief"))

exps = S.list_experiments(); index = []
for e in exps:
    view = VIEWS.get(e["kind"])
    if not view: continue
    d = view(e["name"]); json.dump(d, open(os.path.join(DATA, f"{e['name']}.json"), "w"))
    # collect run paths referenced by the view
    paths = set()
    def walk(o):
        if isinstance(o, dict):
            if "path" in o and isinstance(o["path"], str): paths.add(o["path"])
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(d); n = 0
    for p in sorted(paths):
        r = slim_run(p)
        if r is None: continue
        fp = os.path.join(RUNS, p.replace("/", "__") + ".json"); json.dump(r, open(fp, "w")); n += 1
    index.append(dict(name=e["name"], kind=e["kind"], runs=n))
    print(f"{e['name']:28s} {e['kind']:10s} runs {n}")
json.dump(dict(experiments=index), open(os.path.join(DATA, "index.json"), "w"))
# docs pages
for md in ["WRITEUP.md", "EXPERIMENT_LOG.md", "EXPERIMENT_TABLE.md", "RESULTS_DIGEST.md", "README.md"]:
    if not os.path.exists(os.path.join(ROOT, md)): continue
    body = markdown.markdown(open(os.path.join(ROOT, md)).read(), extensions=["tables", "fenced_code"])
    html = f'<!doctype html><meta charset="utf-8"><title>{md}</title><link rel="stylesheet" href="style.css"><nav><a href="index.html">experiments</a> · <a href="WRITEUP.html">write-up</a> · <a href="EXPERIMENT_LOG.html">log</a> · <a href="EXPERIMENT_TABLE.html">table</a> · <a href="RESULTS_DIGEST.html">digest</a> · <a href="https://github.com/fatemehmd/peer-forensics">repo</a></nav><main class="doc">{body}</main>'
    open(os.path.join(OUT, md.replace(".md", ".html")), "w").write(html)
os.makedirs(os.path.join(OUT, "figs"), exist_ok=True)
for f in glob.glob(os.path.join(ROOT, "figs", "*.png")): shutil.copy(f, os.path.join(OUT, "figs", os.path.basename(f)))
print("docs written")
