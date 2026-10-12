# source-check

An Agent Skill that checks an AI answer against the document it came from.
Every claim in the answer gets a verdict, a page number and a quote from the
document, and a script confirms each quote is really on that page before you
see the table.

```bash
npx skills add TianyiDataScience/source-check
```

It works in Claude Code, Codex, Cursor and other agents that read `SKILL.md`
skills.

## Try it

Clone this repository, open your agent in it and ask:

> Check examples/water-report-answer.md against examples/water-report.pdf

Or use your own files:

> Check this summary against Q3-report.pdf: (paste the summary)

> Is everything in your last answer actually in the contract?

## What you get

From [the example](examples/water-report-check.md), a fictional report and a
summary with planted mistakes:

**Source check: 11 claims. 6 supported, 3 contradicted, 2 not in source.**

| # | Claim | Verdict | Page | Evidence (quoted from the source) | Note |
|---|---|---|---|---|---|
| 1 | "demand reached 42.9 million gallons in September, seasonally adjusted" | ❌ Contradicted | 2 | "Before seasonal adjustment, September demand was 42.9 million gallons" | 42.9 is the unadjusted figure. Seasonally adjusted: 41.2. |
| 2 | "up 3.5% from August" | ✅ Supported | 2 | "41.2 million gallons in September 2026, seasonally adjusted, up from 39.8 million gallons in August" | 41.2 / 39.8 = +3.5% |
| 7 | "The Board raised the base rate to $4.25 per 1,000 gallons" | ❌ Contradicted | 2 | "The Board left the base rate at $4.15 per 1,000 gallons." | Not raised, and $4.15 |
| 9 | "The Authority expects demand to ease in October" | ⚠️ Not in source | 2 | "The Authority does not publish demand forecasts in this report." | Searched: forecast, expect, October |
| 11 | "September figures are final" | ❌ Contradicted | 3 | "Figures for September are preliminary." | |

The full report ends with a "What to fix" list, and the agent can rewrite
the flagged sentences on request.

## Why it checks against the document only

When a model summarizes a long report, the mistakes that matter are
quiet ones. It takes a number from the right table but the wrong column
(unadjusted instead of seasonally adjusted), or from last year's row. It
calls preliminary figures final. It adds a forecast that sounds sensible
and that the document never made.

Fact-check tools that search the web don't catch these, because the
question is whether the answer matches your file. source-check accepts only
the document as evidence. A claim that is true in the world but absent
from your file is marked "not in source", which is what you need to know
before you repeat it.

The agent doing the checking can misquote too. So it writes its claims and
quotes to a JSON file, and `check_quotes.py` looks for every quote in the
extracted text. A quote that is on another page, or nowhere, has to be
fixed before the table goes out.

## How it works

1. `extract_pages.py` turns the document into text with a marker before
   each page. Page numbers are the PDF viewer's; when the PDF prints its own
   numbers and they differ, both are shown.
2. The agent splits the answer into claims of one number, date, name or
   comparison each.
3. `search.py` lists every page where a number or phrase appears. It
   matches `40367` to `40,367` but never to `140,367`, so long documents
   don't have to be read in full.
4. Each claim gets one verdict: ✅ supported, ❌ contradicted, ⚠️ not in
   source, or ❔ can't check (a scanned page or a chart image).
   Changes, ratios and margins are recomputed from the document's own
   figures, with the arithmetic in the note.
5. `check_quotes.py` verifies every quote and page number.
6. The agent reports the totals, the table and what to fix.

The steps and rules the agent follows are in
[skills/source-check/SKILL.md](skills/source-check/SKILL.md).

## Requirements

- Python 3.8 or later.
- For PDFs, either poppler's `pdftotext` (`brew install poppler` or
  `sudo apt install poppler-utils`) or `python3 -m pip install pypdf`. On a
  Mac with neither, it falls back to the PDFKit framework built into macOS.
  Text, Markdown, HTML and .docx files need nothing else.

Scanned PDFs need OCR first. The extraction step lists the pages that have
no text layer.

## Other ways to install

Claude Code plugin marketplace:

```
/plugin marketplace add TianyiDataScience/source-check
/plugin install source-check@source-check
```

By hand, for Claude Code:

```bash
git clone https://github.com/TianyiDataScience/source-check.git
cp -r source-check/skills/source-check ~/.claude/skills/
```

For Codex, copy the same folder to `~/.codex/skills/`.

## Limits

- It checks the answer against the document, not against the world. If the
  document is wrong, a "supported" verdict is wrong too.
- Charts and images are checked only when the agent can see the page image.
- A 300-page filing with 80 claims is still a long job. The agent searches
  first and reads only the pages it needs, but expect it to take a while.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests build the example PDF with plain Python, so they need no
downloads. The PDF tests run when `pdftotext` or `pypdf` is installed.

## Why I made it

I'm Tianyi, and I build [Creatos](https://creatos.io/?utm_source=github&utm_medium=readme&utm_campaign=source-check),
a desktop AI canvas. We test AI models on real documents, such as a 39-page
jobs report, a 10-K and a Fed statement, and every answer on our
[test pages](https://creatos.io/tests?utm_source=github&utm_medium=readme&utm_campaign=source-check)
is checked against the page it came from. This skill is that checking step,
written down so any agent can do it.

Issues and pull requests are welcome, especially documents where the skill
gets a verdict wrong.

## License

MIT
