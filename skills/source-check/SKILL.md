---
name: source-check
description: Check an AI-written answer, summary or report against the source document it is based on (PDF, filing, paper, contract, transcript, notes). Splits the answer into single claims, finds each one in the document, and returns a table with a verdict (supported, contradicted, not in source, can't check), the page number and a verbatim quote, with every quote verified by a script. Use when the user asks to fact-check, verify or audit an answer against a document, to find hallucinations or wrong numbers in a summary, or asks whether something "is right according to the PDF".
license: MIT
metadata:
  author: Tianyi (creatos.io)
  version: "1.0.0"
---

# Source check

Check every claim in an answer against the document it came from. The only
evidence is the document. Your own knowledge and the web are not evidence:
a claim that is true in the world but absent from the document is "not in
source".

Paths to scripts below are relative to this skill's folder. The scripts need
Python 3.8 or later. For PDFs they use poppler's `pdftotext` or the `pypdf`
package (pdfplumber or PyMuPDF also work), whichever is installed.

The examples below use a made-up company, Northwind, so they don't give
away the answers to the example files that come with this skill.

## What you need

1. **The source**: a file (PDF, .txt, .md, .html, .docx) or pasted text.
2. **The answer to check**: pasted text, a file, or an earlier answer in
   this conversation, including your own. Your own answers get no special
   treatment.

If one of them is missing, ask for it once, then start.

## Step 1. Get the source text with page numbers

Use a new working folder for each check, so one check never overwrites
another:

```bash
W="${TMPDIR:-/tmp}/source-check/<short name of the source>"
mkdir -p "$W"
python3 scripts/extract_pages.py "<source file>" -o "$W/source.pages.txt"
```

The output has a `=== Page N ===` line before each page. N is the page
number a PDF viewer shows, and it is the number you report. When the PDF
file defines its own page labels (and pypdf is installed), the marker shows
the label too, for example `=== Page 26 (printed: 24) ===`, and you write
"p. 26 (printed 24)". This works whichever tool extracted the text. Many
PDFs have no labels, and numbers printed only in a page's footer are not
detected; if you notice they differ from the viewer's, say so once above
the table.

Read the summary the script prints. Pages with almost no text are usually
scans or images. Claims that depend on them get "can't check" unless you
can read the page image itself. For pasted text, save it to a .txt file
and run the same command; it becomes a single page, so cite the section
heading instead of a page.

## Step 2. Split the answer into claims

A claim is one statement that can be true or false: one number, one date,
one name, one comparison, one cause.

- Give each number its own row. "Revenue rose to $4.2 billion from $3.9
  billion" is two rows: $4.2 billion this year, $3.9 billion last year.
  "Rose" needs no row of its own; it is right if both numbers are.
- A direction stays with the size it describes: "up 8% from 2024" is one
  row.
- Keep the qualifiers with the claim: seasonally adjusted, preliminary,
  per share, in millions, year over year, "about", "at least".
- A claim that something is absent ("the report gives no forecast") is a
  claim too. Check it by searching.
- Headings and titles count only when they state a fact, such as a
  period, a name or a number. Each such fact gets its own row.
- Leave out greetings, questions, advice and the answer's own opinions.
  List them under "Not checked" at the end if they could mislead.
- Number the claims in the order they appear and keep the answer's words.
  When the answer numbers its own items, start the Claim cell with that
  number, for example "(item 3) Commercial use fell", so the reader can
  find it.

If you would call a claim "partly supported", split it until each part
gets one verdict.

## Step 3. Find the evidence

Read the whole pages file if the document is under about 30 pages.
Otherwise search first and read only the pages that matter:

```bash
python3 scripts/search.py "$W/source.pages.txt" "operating margin" "4.2" "Cloud" -C 2
```

`search.py` ignores case, matches phrases across line breaks, and matches
numbers with or without thousands separators but never inside a longer
number (`40367` finds `40,367` but not `140,367`). Words match inside
longer words, so a stem like `compar` finds "compare" and "comparison".

For each claim, check all of these, not only the number:

- the right row and the right column of a table (read the headers);
- the right period: month, quarter, fiscal or calendar year, year to date;
- seasonally adjusted or not, preliminary or revised, GAAP or adjusted;
- the right unit and scale: thousands or millions, percent or percentage
  points, basis points;
- the right entity: the segment or the whole company, the parent or a
  subsidiary;
- who said it, for quotes and attributions.

For a derived number (a change, a ratio, a margin, a sum), find the inputs
in the document and recompute it. Write the arithmetic in the note, for
example "1,310 / 5,870 = 22.3%". Rounding to the precision the answer used
counts as a match.

## Step 4. Give each claim a verdict

| Verdict | Use it when |
|---|---|
| ✅ Supported | The document states it, or it follows by arithmetic you show. |
| ❌ Contradicted | The document says something that can't be true at the same time: another number, the other direction, "no change" against "a cut" for the same period. Give the document's version. |
| ⚠️ Not in source | The document doesn't say it, though it may be true elsewhere. Also use it when the document touches the subject but doesn't settle the claim; quote the nearest passage. |
| ❔ Can't check | The part you need can't be read: a scan, a chart image, missing pages. |

More rules:

- Never mark a claim supported because you know it is true.
- Right number, missing qualifier: supported, and the note names what the
  reader needs (the month, "seasonally adjusted", "preliminary"). It is
  contradicted only when the answer's words say the opposite, for example
  "final" for preliminary figures, or "seasonally adjusted" for an
  unadjusted figure.
- A quote or statement stretched to say more ("expects no change" turned
  into "ruled out a change"): contradicted if the document's words rule
  the claim out, otherwise not in source, with the real words in the note.
- Before you mark a claim "not in source", search for at least three
  likely words or numbers. You will list them in `searched` (Step 5).

## Step 5. Verify your own quotes

You can misquote too, so the table goes out only after a script finds every
quote in the document. Write the claims to `$W/claims.json`:

```json
{"claims": [
  {"id": 1, "verdict": "contradicted", "page": 41, "quote": "Cloud ... 5,870 6,940"},
  {"id": 2, "verdict": "supported", "page": 12, "quote": "operating income of $1,310 million"},
  {"id": 3, "verdict": "not_in_source", "searched": ["guidance", "outlook", "2027"]},
  {"id": 4, "verdict": "not_in_source", "page": 18, "quote": "We do not provide revenue guidance", "searched": ["guidance", "forecast", "expect"]}
]}
```

Copy quotes from the pages file; don't retype them. Keep each one short:
the words that prove the point. For a table, quote the row label, then
` ... `, then the cells you read, in the order they appear; name the
column in the Note. The script checks that those cells are on the row
label's line. `page` can be a number, "26-27" for a quote that runs across
a page break, or a list. A `not_in_source` claim needs `searched`, and can
also have a quote of the nearest passage.

```bash
python3 scripts/check_quotes.py "$W/source.pages.txt" "$W/claims.json"
```

Fix every blocking line and run it again until it exits with 0:

- **WRONG PAGE**: cite the page the script names.
- **OTHER ROW**: the cells you quoted belong to another row of the table.
  Read the row again and fix the quote, and the verdict if it changes.
- **NOT FOUND**: copy the quote again from the pages file. Numbers must
  match exactly, with the same thousands separators, and "41.2" does not
  pass for "41.25". If the quote runs across a page break, cite a range.
  If the words really aren't there, the verdict was wrong: change it.
- **NO QUOTE**: add a quote, or change the verdict.
- **NO SEARCH**: add the terms you searched for.
- **BAD VERDICT**: use one of the four verdicts.

A line may also say that searched terms appear on some pages. That note
doesn't block: read those passages, and keep "not in source" only if none
of them makes the claim.

## Step 6. Report

Start with one line of totals, then the table, then what to fix.

```markdown
**Source check: 5 claims. 2 supported, 2 contradicted, 1 not in source.**
Source: northwind-annual-report.pdf (88 pages). Answer: the summary in summary.md.

| # | Claim | Verdict | Page | Evidence (quoted from the source) | Note |
|---|---|---|---|---|---|
| 1 | "Cloud revenue was $6.9 billion in 2025" | ❌ Contradicted | 41 | "Cloud ... 5,870 6,940" (segment table) | $6,940 million is 2024. 2025: $5,870 million. |
| 2 | "an operating margin of 22%" | ✅ Supported | 12 | "operating income of $1,310 million" | 1,310 / 5,870 = 22.3% |
| 3 | "management expects double-digit growth in 2027" | ⚠️ Not in source | 18 | "We do not provide revenue guidance" | Searched: guidance, forecast, expect |
| 4 | "the board approved a $2 billion buyback" | ❌ Contradicted | 55 | "authorized the repurchase of up to $1.5 billion" | $1.5 billion, not $2 billion |
| 5 | "headcount grew to 12,400" | ✅ Supported | 9 | "12,400 full-time employees" | At 31 December 2025 |

**What to fix**
- #1: Cloud revenue was $5,870 million in 2025 (p. 41).
- #3: remove it; the report gives no guidance (p. 18).
- #4: the buyback is up to $1.5 billion (p. 55).
```

Rules for the report:

- In the header, say where the answer came from: a file name, "the
  summary pasted above", or "your answer earlier in this conversation".
- Quote the answer's words in the Claim column, shortened with "..." if
  long. Quote the document's words in the Evidence column.
- When a claim has no page or quote, write "none" in those columns. Leave
  the Note empty when there is nothing to add.
- The Note says what is wrong and what the document says, in a few words.
  No comments on the model or the person who wrote the answer.
- "What to fix" lists only the ❌ and ⚠️ rows. If you left out statements
  that could mislead (Step 2), list them after it under **Not checked**.
- If the user asks for a corrected answer, change only the sentences with
  ❌ or ⚠️, cite the page next to each change, and keep everything else as
  it was.
- With several source files, write the page as `file.pdf p. 12`.

## Traps worth checking every time

- A number that exists in the document but in another row, column or year.
- Seasonally adjusted against unadjusted figures in the same table.
- A change computed from one adjusted and one unadjusted figure.
- Preliminary figures described as final.
- Percent change confused with percentage points.
- A total described as a segment, or the other way round.
- Monthly figures presented as quarterly or yearly.
- "Record", "highest", "first", "lowest" or "only" with no support in the
  document.
- True background facts the document never states.
- A real quote stretched to say more than it does.
- Invented precision: "41.23" when the document says "41.2".

## Example files

The repository this skill comes from,
https://github.com/TianyiDataScience/source-check, has an `examples/`
folder (not inside this skill folder) with a short fictional report, an
AI summary of it with planted mistakes, and the check this skill produced.
