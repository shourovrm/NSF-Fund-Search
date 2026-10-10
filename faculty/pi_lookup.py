# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run the web lookups with the pi agent, a cheap model and Tavily search.

Usage:
    TAVILY_API_KEY=... uv run faculty/pi_lookup.py

Looks up every data/faculty/cache/web/lookup_NN.jsonl that has no
results_NN.jsonl yet, so an interrupted run continues where it stopped. pi must
have the Tavily server configured:
    pi mcp add tavily --url https://mcp.tavily.com/mcp/ --bearer-token-env-var TAVILY_API_KEY
"""

import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

import web_lookup

MODEL = "openrouter/z-ai/glm-5.3-flash"
# pi shows the Tavily server as one tool; read and write handle the lookup and results files.
TOOLS = "read,write,mcp__tavily"
PROMPT_PATH = Path(__file__).resolve().parent / "web_lookup_prompt.md"
PARALLEL_RUNS = 4
RUN_TIMEOUT_SECONDS = 1200


def run_lookup(lookup_path):
    results_path = lookup_path.with_name(lookup_path.name.replace("lookup_", "results_"))
    prompt = PROMPT_PATH.read_text().format(lookup_path=lookup_path, results_path=results_path)
    command = ["pi", "--print", "--no-session", "--no-skills", "--no-context-files",
               "--model", MODEL, "--thinking", "low", "--tools", TOOLS, prompt]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=RUN_TIMEOUT_SECONDS)
        last_line = (completed.stdout.strip().splitlines() or ["no reply"])[-1]
    except subprocess.TimeoutExpired:
        last_line = "timed out"
    status = "written" if results_path.exists() else "NO RESULTS FILE"
    return f"{lookup_path.name}: {status}; {last_line[:200]}"


def main():
    if not os.environ.get("TAVILY_API_KEY"):
        sys.exit("TAVILY_API_KEY is not set")
    pending = [
        path for path in sorted(web_lookup.WEB_DIR.glob("lookup_*.jsonl"))
        if not path.with_name(path.name.replace("lookup_", "results_")).exists()
    ]
    print(f"{len(pending)} lookup files to run", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLEL_RUNS) as executor:
        for summary in executor.map(run_lookup, pending):
            print(summary, flush=True)


if __name__ == "__main__":
    main()
