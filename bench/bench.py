#!/usr/bin/env python3
"""Token benchmark for Kanso: runs one task with and without Kanso, side by side.

From inside any git repo:
  python3 ~/Documents/kanso-plugin/bench/bench.py "add validation to the signup form"

Each run works on a temporary clone of your last commit, so your files are
never touched. Kanso is loaded from this repo, so local edits to kanso.md count.
"""
import argparse
import datetime
import json
import statistics
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "bench" / "results"
# Disable the installed copy so only --plugin-dir decides whether Kanso loads.
NO_INSTALLED = json.dumps({"enabledPlugins": {"kanso@kanso": False}})
# No shell: the project's commands are unknown, and both arms get the same tools.
TOOLS = ["Read", "Glob", "Grep", "Edit", "Write"]
METRICS = ["total_tokens", "in_tokens", "out_tokens", "cost", "turns", "reply_lines", "diff_lines"]


def git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=bench", "-c", "user.email=bench@localhost", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout


def run_once(repo, prompt, kanso, model):
    with tempfile.TemporaryDirectory() as ws:
        git(ws, "clone", "-q", "--local", repo, ".")
        cmd = ["claude", "-p", "--output-format", "json", "--settings", NO_INSTALLED]
        if kanso:
            cmd += ["--plugin-dir", str(ROOT)]
        if model:
            cmd += ["--model", model]
        cmd += ["--allowedTools", *TOOLS]
        proc = subprocess.run(cmd, input=prompt, cwd=ws, capture_output=True, text=True, timeout=900)
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"error": (proc.stderr or proc.stdout).strip()[:300]}

        git(ws, "add", "-A")
        numstat = git(ws, "diff", "--cached", "--numstat")
        diff_lines = sum(int(a) + int(d) for a, d, _ in (l.split("\t") for l in numstat.splitlines()) if a != "-")
        # modelUsage covers every model the session called, background ones included.
        usage = out.get("modelUsage", {}).values()
        in_tokens = sum(u["inputTokens"] + u["cacheReadInputTokens"] + u["cacheCreationInputTokens"] for u in usage)
        out_tokens = sum(u["outputTokens"] for u in usage)
        reply = out.get("result") or ""
        return {
            "total_tokens": in_tokens + out_tokens,
            "in_tokens": in_tokens,
            "out_tokens": out_tokens,
            "cost": out.get("total_cost_usd", 0),
            "turns": out.get("num_turns", 0),
            "reply_lines": sum(1 for l in reply.splitlines() if l.strip()),
            "diff_lines": diff_lines,
            "error": out.get("subtype") if out.get("is_error") else None,
            "reply": reply,
        }


def main():
    ap = argparse.ArgumentParser(description="Run a task with and without Kanso and compare tokens.")
    ap.add_argument("prompt", help="the task, as you'd type it to Claude")
    ap.add_argument("--runs", type=int, default=1, help="runs per side (default 1; 3 for steadier numbers)")
    ap.add_argument("--model", help="model to test (default: your Claude Code default)")
    args = ap.parse_args()

    try:
        repo = git(Path.cwd(), "rev-parse", "--show-toplevel").strip()
    except subprocess.CalledProcessError:
        raise SystemExit("Run this from inside a git repo.")
    if git(repo, "status", "--porcelain"):
        print("Note: uncommitted changes aren't copied. The test uses your last commit.")

    rows = []
    with ThreadPoolExecutor(2 * args.runs) as pool:
        futures = {pool.submit(run_once, repo, args.prompt, arm == "with", args.model): arm
                   for arm in ("with", "without") for _ in range(args.runs)}
        for fut in as_completed(futures):
            arm = futures[fut]
            try:
                r = fut.result()
            except (subprocess.SubprocessError, OSError) as e:
                r = {"error": str(e)[:300]}
            r["arm"] = arm
            rows.append(r)
            print(f"{arm} Kanso: " + (f"error: {r['error']}" if r.get("error") else f"{r['total_tokens']} tokens"),
                  flush=True)

    RESULTS.mkdir(parents=True, exist_ok=True)
    log = RESULTS / f"{datetime.datetime.now():%Y-%m-%dT%H-%M-%S}.jsonl"
    log.write_text("".join(json.dumps(r | {"repo": repo, "prompt": args.prompt}) + "\n" for r in rows))

    def med(arm, m):
        vals = [r[m] for r in rows if r["arm"] == arm and not r.get("error")]
        return statistics.median(vals) if vals else 0

    print(f"\n{'':14}{'with Kanso':>12}{'without':>12}{'change':>9}")
    for m in METRICS:
        w, wo = med("with", m), med("without", m)
        fmt = (lambda x: f"{x:.3f}") if m == "cost" else (lambda x: f"{x:g}")
        print(f"{m:14}{fmt(w):>12}{fmt(wo):>12}{(f'{(w - wo) / wo:+.0%}' if wo else 'n/a'):>9}")
    print(f"\nReplies saved in {log}")


if __name__ == "__main__":
    main()
