---
name: deslop
description: >-
  Score fetched web pages for ads, slop, SEO and second-hand content, one probability each,
  with TypeSafe's Jev model. Read this before reading any page fetched for research (news,
  leads, purchases, health): run the page bodies through deslop first and set your own
  thresholds. Not for search snippets or titles; the runner refuses them.
---

# deslop

Four probabilities per page, no verdict. The caller decides what to drop.

```
skills/deslop/deslop.py < pages.jsonl        # {"id": ..., "url": ..., "text": <page body>} per line
```

Output, one line per input, in order:

```
{"id": "a1", "url": "https://…", "scores": {"ad": 0.91, "slop": 0.12, "seo": 0.80, "derivative": 0.77}}
{"id": "a2", "url": "https://…", "error": "text too short (140 < 250 chars): send the page body, not a snippet"}
```

Options: `--min-chars N` (default 250) · `--threads N` (default 8) · `--experimental` adds dimensions held for eval (`clickbait`). Needs `TYPESAFE_API_KEY`, or a proxy that injects it for `api.typesafe.ai`.

## The scores

Each is the probability (0–1) that the label applies to the page as a whole.

| Score | 1 means | 0 means |
| --- | --- | --- |
| `ad` | The page exists to sell or promote: pitch, affiliate roundup, sponsored post, press release, landing page, a company announcing its own product | Reports, explains, documents or argues; any product mentioned is incidental |
| `slop` | Reads as machine-generated filler: uniform rhythm, hedged padding, no names, dates, numbers or first-hand detail | A person with something to say: specific facts, uneven voice, opinions that could be wrong |
| `seo` | Written for the ranking algorithm: keyword where a pronoun would do, query-echo headings, listicle with no reason to be one, "ultimate guide" / "best X of YEAR" | Written the way the author would explain it to a colleague |
| `derivative` | Restates other coverage or data without naming a source: "reports say", "experts believe", a rewrite of an announcement with no link | The author is the actor, the data's publisher or a witness; or a reporter who names and links primary sources |

Read them together, not one at a time. A press release is `ad` ≈ 1 and `derivative` ≈ 0: it is promotional and primary at once, and for "what did the company say" it is the right source. A newsletter that links every item it summarises is `derivative` ≈ 0. A landing page that is short, honest and specific is still `ad` ≈ 1; that is the point of the page, not a flaw in it.

## Using it in a consumer

Run every page fetched for research through deslop before reading it, set thresholds per use, and grade the first real batch by hand against your own reading before trusting it unattended. Thresholds belong to the consumer, not here; sensible starting points: drop `slop` ≥ 0.5 for reading material, drop `ad` ≥ 0.7 unless the product itself is the topic, treat `derivative` ≥ 0.6 as "find the primary source", never as a source.

Give it the body, not the search snippet. Scores on a snippet or a title are noise, which is why the runner refuses input under the floor. Long pages are cut at 12,000 characters; the lead decides the scores anyway.

## Known limits

Measured on `eval/labelled.jsonl` (38 pages, hand-labelled, see README for the table): `ad` and `slop` are reliable; `seo` and `derivative` miss on the recall side. The model reads `seo` narrowly (keyword stuffing, query headings) and does not flag a template essay with real names in it. It reads `derivative` as "rewrites coverage" and does not flag an affiliate roundup that restates spec sheets. Japanese pages score as well as English ones on this set, but the set holds only six; check the first Japanese batch by hand.

## Adding a dimension

`questions.json` is a map of TypeSafe `noul` questions. Add one, label it in `eval/labelled.jsonl`, run `eval/run.py`. A dimension ships (is listed in `SHIPPED` in `deslop.py` and gated in the eval) once its accuracy is above the gate; until then it is `--experimental`.

`jev.py` is the generic batch runner (any TypeSafe question set, one request per item, parallel); `deslop.py` is the thin layer with the input contract and the fixed questions.
