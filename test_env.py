"""Scripted agent: sanity-check the mocked environment and metrics without an API."""
import env as E
for cond in E.CONDITIONS:
    e = E.Env(cond)
    print("==", cond)
    print(e.call("list_dir", {"path": "/shared/cache"}))
    if "/shared/cache/README.txt" in e.fs: e.call("read_file", {"path": "/shared/cache/README.txt"})
    for d in [E.BOARD_DIR, "/shared/cache"]:
        b = e.call("list_dir", {"path": d})
        if not b.startswith("ERROR"):
            for f in b.split("\n"):
                if not f.endswith("/"): print("   ", f, "->", e.call("read_file", {"path": f"{d}/{f}"})[:90].replace("\n"," | "))
    print(e.call("http_get", {"url": E.COMPANIES[0][1]}))
    print(e.call("http_get", {"url": "http://artifact-cache.internal/remote/" + E.COMPANIES[0][1]}))
    e.call("write_file", {"path": "/workspace/sheet.csv", "content": E.sheet_csv().replace("Halvex Robotics,https://ir.halvex.com/annual-2025,", "Halvex Robotics,https://ir.halvex.com/annual-2025,412")})
    e.call("report_to_operator", {"message": "blocked"}); e.call("submit", {"note": "partial"})
    print(e.metrics)
