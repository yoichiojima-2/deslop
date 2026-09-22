#!/usr/bin/env python3
"""Classify, score or yes/no-judge many items with TypeSafe's Jev model, one API call per item.

Usage:
  jev.py --questions QUESTIONS.json [--threads N] < items
  jev.py --questions QUESTIONS.json --state "one item"

Items on stdin: one per line. A line that is a JSON object is passed as the state as is
(keep an "id" field to recognise it in the output); any other line is a plain-text state.
Output: one JSON line per item, in input order: {"id": ..., "state": ..., "answers": {...}}.
Questions: a JSON object in the TypeSafe request format (map of name -> {type, instructions, criteria}).

Needs TYPESAFE_API_KEY, or a proxy that injects it for api.typesafe.ai (cloud sessions).
"""
import argparse, json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"


def ask(state, questions):
    body = json.dumps({"state": state, "model": MODEL, "questions": questions}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + os.environ.get("TYPESAFE_API_KEY", "proxy-injected"),
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"}
    except Exception as e:  # network, timeout
        return {"error": str(e)}


def parse_item(line):
    line = line.rstrip("\n")
    if line.startswith("{"):
        try:
            obj = json.loads(line)
            return obj.get("id"), obj
        except json.JSONDecodeError:
            pass
    return None, line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True, help="path to a JSON file with the questions map")
    ap.add_argument("--state", help="a single item instead of stdin")
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()
    with open(a.questions) as f:
        questions = json.load(f)
    lines = [a.state] if a.state is not None else [l for l in sys.stdin if l.strip()]
    items = [parse_item(l) for l in lines]
    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        results = list(ex.map(lambda it: ask(it[1], questions), items))
    usage_in = usage_out = 0
    for (id_, state), r in zip(items, results):
        out = {"id": id_, "state": state}
        if "error" in r:
            out["error"] = r["error"]
        else:
            out["answers"] = r["answers"]
            usage_in += r.get("usage", {}).get("input_tokens", 0)
            usage_out += r.get("usage", {}).get("output_tokens", 0)
        print(json.dumps(out, ensure_ascii=False))
    print(f"jev: {len(items)} items, {usage_in} in / {usage_out} out tokens", file=sys.stderr)


if __name__ == "__main__":
    main()
