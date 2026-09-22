# deslop

An agent skill (Claude Code plugin) that scores fetched web pages for ads, slop, SEO and second-hand content before the agent reads them. Built on [TypeSafe](https://docs.typesafe.ai) Jev: four probabilities per page, no verdict, the caller sets the thresholds.

```
skills/deslop/deslop.py < pages.jsonl
{"id": "a1", "url": "https://…", "scores": {"ad": 0.91, "slop": 0.12, "seo": 0.80, "derivative": 0.77}}
```

Input is one page per line: `{"id", "url", "text"}` where `text` is the page body. Snippets and titles are refused (default floor 250 characters). Needs `TYPESAFE_API_KEY`.

Try it on the bundled examples (get a key at [typesafe.ai](https://typesafe.ai)):

```
export TYPESAFE_API_KEY=...
skills/deslop/deslop.py < skills/deslop/examples/pages.jsonl
```

| Score | 1 means |
| --- | --- |
| `ad` | exists to sell or promote: pitch, affiliate roundup, sponsored post, press release |
| `slop` | reads as machine-generated filler: uniform rhythm, hedged padding, no names, dates or first-hand detail |
| `seo` | written for the ranking algorithm: keyword stuffing, listicle shape, query-echo headings |
| `derivative` | restates other coverage without naming a source |

Full definitions, how to read them together, and the consumer paragraph: [skills/deslop/SKILL.md](skills/deslop/SKILL.md).

## Install

As a Claude Code plugin:

```
/plugin marketplace add yoichiojima-2/deslop
/plugin install deslop@deslop
```

For any other agent, the skill is the `skills/deslop/` directory, in the [agent skill](https://agentskills.io) format (a `SKILL.md` with frontmatter plus files). Copy it into your agent's skills directory and pin the version:

```
cp -r skills/deslop/ <your-repo>/.claude/skills/deslop/      # or wherever your agent reads skills
```

Record `deslop vX.Y.Z @ <sha>` where you keep vendored versions. Re-sync on tagged releases only; when something is wrong downstream, open an issue here rather than patching the copy.

Runtime: Python 3.9+, no dependencies beyond the standard library.

## How it grades

`eval/labelled.jsonl` is a hand-labelled adversarial set: SEO farms that mimic journalism, human writing that sounds generic, sponsored posts marked editorial, Japanese pages, primary sources with marketing tone, affiliate roundups, derivative rewrites, template essays with real names in them. Every page is written for the set with fictional outlets and companies; none is scraped.

`eval/run.py` scores it and prints accuracy, precision and recall per dimension at a 0.5 cut, exiting non-zero when a shipped dimension falls under the gate (`--gate`, default 0.85). Run it after any change to `questions.json`.

v1.0.0 (unchanged in v1.0.1), 38 pages, 2026-09-22, two runs identical except one `slop` item that sat at 0.49 once:

| dimension | n | accuracy | precision | recall |
| --- | --- | --- | --- | --- |
| `ad` | 38 | 1.00 | 1.00 | 1.00 |
| `slop` | 38 | 0.97–1.00 | 1.00 | 0.94–1.00 |
| `seo` | 38 | 0.89 | 1.00 | 0.69 |
| `derivative` | 38 | 0.87 | 1.00 | 0.69 |
| `clickbait` (experimental) | 38 | 0.97 | 1.00 | 0.67 |

Read the numbers for what they are. The set was labelled by one person, so accuracy is agreement with that person, not ground truth. Thirty-eight pages is enough to catch a broken question, not to distinguish 0.87 from 0.92. The misses are all on the recall side and all in the same place: `seo` does not fire on a template essay that has real names in it (the two "slop with names" pages, the Japanese matome); `derivative` does not fire on affiliate roundups, where the label itself is arguable (they restate spec sheets, not coverage). Precision is 1.00 everywhere: on this set the scorer does not flag good pages, which is the failure that would matter most for a research filter.

## Known limits

- The definitions are the model's reading of the questions in `questions.json`, not yours. Grade the first real batch of any new use by hand.
- Slop generators change; a set written in 2026-09 will date. The eval runs monthly in CI for that reason, and the set needs new pages when a miss shows up downstream.
- Six Japanese pages is not a Japanese eval. Nothing in the set is in a third language.
- Scores are per page; a good article with a sponsored box at the end scores as the article.
- "Slop" is a recent coinage. If the word dates, the definition in SKILL.md is what the score means.

## Contributing

The most useful contribution is a page the scorer gets wrong: open an issue with the page body, the labels you would give it and why, and it goes into `eval/labelled.jsonl`. Pages in the set are written for it, not scraped, so rewrite the shape of the page you found rather than pasting it. Changes to `questions.json` need the eval table in this README updated from a fresh `eval/run.py`.

## Layout

```
skills/deslop/    the skill: SKILL.md, questions.json, deslop.py, jev.py, examples/pages.jsonl
eval/             labelled.jsonl, run.py
.github/workflows/eval.yml   runs the eval on push and monthly; needs the TYPESAFE_API_KEY secret
```

MIT.
