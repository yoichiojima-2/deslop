#!/usr/bin/env python3
"""deslop: score web pages for ads, slop, SEO and second-hand content.

Usage:
  deslop.py < pages.jsonl                 # one page per line: {"id": ..., "url": ..., "text": ...}
  deslop.py --min-chars 250 --threads 8 < pages.jsonl

Output, one JSON line per input line, in input order:
  {"id": ..., "url": ..., "scores": {"ad": 0.91, "slop": 0.12, "seo": 0.80, "derivative": 0.77}}
Each score is the probability (0-1) that the label applies. No verdict: the caller sets thresholds.

A line whose "text" is shorter than --min-chars (default 250) is refused:
  {"id": ..., "url": ..., "error": "text too short (123 < 250 chars): send the page body, not a snippet"}
Scores on a search snippet or a title are noise, so the floor is deliberate.

Questions live in questions.json next to this file; add a dimension by adding a noul question.
Needs TYPESAFE_API_KEY, or a proxy that injects it for api.typesafe.ai.
"""
import argparse, json, os, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from jev import ask  # noqa: E402

SHIPPED = ["ad", "slop", "seo", "derivative"]
MAX_CHARS = 12000  # Jev context is finite; the lead of a page decides the scores anyway


def load_questions(path, experimental):
    with open(path) as f:
        q = json.load(f)
    if not experimental:
        q = {k: v for k, v in q.items() if k in SHIPPED}
    return q


def score(item, questions, min_chars):
    text = item.get("text") or ""
    if len(text) < min_chars:
        return {"error": f"text too short ({len(text)} < {min_chars} chars): send the page body, not a snippet"}
    state = {"url": item.get("url", ""), "text": text[:MAX_CHARS]}
    r = ask(state, questions)
    if "error" in r:
        return {"error": r["error"]}
    scores = {k: round(v["noul"], 3) for k, v in r["answers"].items() if v.get("type") == "noul"}
    return {"scores": scores, "usage": r.get("usage", {})}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions", default=os.path.join(HERE, "questions.json"))
    ap.add_argument("--min-chars", type=int, default=250)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--experimental", action="store_true", help="also return dimensions held for eval (clickbait)")
    a = ap.parse_args()
    questions = load_questions(a.questions, a.experimental)
    items = []
    for n, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            items.append({"id": f"line-{n}", "error": "not a JSON object"})
    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        results = list(ex.map(lambda it: it if "error" in it else score(it, questions, a.min_chars), items))
    tokens_in = tokens_out = 0
    for it, r in zip(items, results):
        out = {"id": it.get("id"), "url": it.get("url")}
        if "error" in r:
            out["error"] = r["error"]
        else:
            out["scores"] = r["scores"]
            tokens_in += r["usage"].get("input_tokens", 0)
            tokens_out += r["usage"].get("output_tokens", 0)
        print(json.dumps(out, ensure_ascii=False))
    print(f"deslop: {len(items)} pages, {tokens_in} in / {tokens_out} out tokens", file=sys.stderr)


if __name__ == "__main__":
    main()
