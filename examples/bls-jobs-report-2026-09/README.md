# Three models summarize the September 2026 jobs report

The source is *The Employment Situation — September 2026* from the U.S.
Bureau of Labor Statistics, released October 2, 2026: 39 pages of text and
tables. It is a U.S. government work in the public domain:
https://www.bls.gov/news.release/archives/empsit_10022026.pdf

Each model got the report's text and this prompt:

> Summarize this report in 10 bullet points for a reader who won't open it.
> Include the key numbers.

Then source-check checked each answer against the PDF.

| Model | Claims | ✅ Supported | ❌ Contradicted | ⚠️ Not in source | Files |
|---|---|---|---|---|---|
| claude-sonnet-5-5 | 51 | 51 | 0 | 0 | [answer](claude-sonnet-5-5/answer.md), [check](claude-sonnet-5-5/report.md) |
| gpt-6.1-sol | 47 | 46 | 0 | 1 | [answer](gpt-6.1-sol/answer.md), [check](gpt-6.1-sol/report.md) |
| gemini-3.1-pro-preview | 28 | 27 | 0 | 1 | [answer](gemini-3.1-pro-preview/answer.md), [check](gemini-3.1-pro-preview/report.md) |
| **Total** | **126** | **124** | **0** | **2** | |

All three got every number right. The two flags are sentences that
describe the report in words the report doesn't use.

## The two flagged claims

**gpt-6.1-sol, claim 40**: "The household survey estimated 406,000 more
employed people, though the report characterized the change as small."

The 406,000 is in Summary table A (p. 4), but the report's text never
describes that change. The nearest words, "changed little" (p. 2), are
about the participation rate and the employment-population ratio. Page 6
puts the household survey's significance threshold at about 650,000, so
the change isn't statistically significant, and a reader could fairly
call it small. The report itself doesn't, so the verdict is "not in
source" rather than "contradicted".

**gemini-3.1-pro-preview, claim 16**: the heading "Healthcare Leads Job
Gains".

The report doesn't rank industries. Health care added 17,000 jobs (p. 2).
In Table B-1, trade, transportation, and utilities added 18,000 (p. 29),
and private education and health services, which includes health care,
added 20,000 (p. 30).

## How it was run

- **Answers**: one API call per model through each provider's API. The
  message was the report's text (extracted with pdf.js) inside
  `<document>` tags, a blank line, then the prompt. No system prompt,
  default settings, at most 8,192 output tokens, no tools. The three calls
  cost $0.48 in total.
- **Checks**: Claude Code on a Mac followed
  [SKILL.md](../../skills/source-check/SKILL.md) once per answer. Neither
  pdftotext nor pypdf was installed, so the page text came from macOS
  PDFKit. Page numbers are the PDF viewer's. `check_quotes.py` exited with
  0 on all three claims files. The three checks took about 25 minutes
  together, most of it one read of pages 1 to 6 and the tables.
- **Retries**: the first gpt-6.1-sol request returned HTTP 503 with no
  answer and was sent once more about 20 seconds later. Nothing else was
  retried, and each model's only answer is the one shown here.
- **Who checked whom**: the checking agent is a Claude model, and one of
  the answers is Claude's. Every verdict cites a page and a quote, so you
  can check the checker.

## Check it yourself

Download the PDF from the link above, then from the repository root:

```bash
python3 skills/source-check/scripts/extract_pages.py empsit_10022026.pdf -o empsit.pages.txt
python3 skills/source-check/scripts/check_quotes.py empsit.pages.txt examples/bls-jobs-report-2026-09/gpt-6.1-sol/claims.json
```

The quotes were checked against PDFKit's text. pdftotext and pypdf can
lay out a table row differently, so a table quote may come back OTHER ROW
or NOT FOUND with them even though the numbers are on the cited page.
