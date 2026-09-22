#!/usr/bin/env python3
"""Score eval/labelled.jsonl with skill/deslop.py and print per-dimension accuracy against the labels.

  eval/run.py [--gate 0.85] [--show-misses]

Labels are 0/1 per dimension; a score >= 0.5 counts as 1. Prints accuracy, precision, recall and
the misses. Exits 1 when any shipped dimension's accuracy is below --gate (clickbait is reported,
never gated).
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESLOP = os.path.join(HERE, "..", "skill", "deslop.py")
SHIPPED = ["ad", "slop", "seo", "derivative"]
EXPERIMENTAL = ["clickbait"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=os.path.join(HERE, "labelled.jsonl"))
    ap.add_argument("--gate", type=float, default=0.85)
    ap.add_argument("--show-misses", action="store_true")
    a = ap.parse_args()
    items = [json.loads(l) for l in open(a.labels) if l.strip()]
    inp = "".join(json.dumps({k: it[k] for k in ("id", "url", "text")}, ensure_ascii=False) + "\n" for it in items)
    p = subprocess.run([sys.executable, DESLOP, "--experimental"], input=inp, capture_output=True, text=True)
    if p.returncode:
        sys.exit(p.stderr)
    outs = {json.loads(l)["id"]: json.loads(l) for l in p.stdout.splitlines() if l.strip()}
    errors = [(i, o["error"]) for i, o in outs.items() if "error" in o]
    for i, e in errors:
        print(f"error {i}: {e}", file=sys.stderr)
    scored = [it for it in items if "scores" in outs.get(it["id"], {})]

    print(f"{'dimension':<12}{'n':>4}{'acc':>7}{'prec':>7}{'rec':>7}  misses")
    failed = False
    for dim in SHIPPED + EXPERIMENTAL:
        tp = fp = fn = tn = 0
        misses = []
        for it in scored:
            y = it["labels"][dim]
            s = outs[it["id"]]["scores"][dim]
            yhat = int(s >= 0.5)
            if yhat and y: tp += 1
            elif yhat and not y: fp += 1; misses.append(f"{it['id']}={s:.2f}(0)")
            elif not yhat and y: fn += 1; misses.append(f"{it['id']}={s:.2f}(1)")
            else: tn += 1
        n = tp + fp + fn + tn
        acc = (tp + tn) / n if n else 0
        prec = tp / (tp + fp) if tp + fp else 1.0
        rec = tp / (tp + fn) if tp + fn else 1.0
        tag = "" if dim in SHIPPED else " (experimental, not gated)"
        print(f"{dim:<12}{n:>4}{acc:>7.2f}{prec:>7.2f}{rec:>7.2f}  {' '.join(misses) if a.show_misses else len(misses)}{tag}")
        if dim in SHIPPED and acc < a.gate:
            failed = True
    if errors:
        print(f"{len(errors)} items errored", file=sys.stderr)
        failed = True
    print(p.stderr.strip(), file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
