#!/usr/bin/env python3
"""Check that every quote in a source-check table is really in the source.

    python3 check_quotes.py source.pages.txt claims.json

claims.json holds the claims you are about to report, as a list or as
{"claims": [...]}. Each claim looks like this:

    {"id": 3, "verdict": "contradicted", "page": 33,
     "quote": "Leisure and hospitality ... 23.90"}

- verdict: supported, contradicted, not_in_source or cant_check.
- page: a number, "26-27", "p. 26", or a list of numbers.
- quote: words copied from the source. Use " ... " between pieces taken
  from the same page or page range, for example a table row label and the
  cells you read. The pieces must appear in that order, and numbers quoted
  after a row label must be on the label's line (set "split_row": true if
  the extracted table really breaks that row over two lines).
- searched: the terms you looked for. Required for not_in_source. The
  script reports every page where one of them appears, so you can read
  those passages before you keep the verdict.

The comparison ignores case, the kind of quote marks and dashes, line
breaks, runs of spaces and words split by a hyphen at the end of a line.
A number in a quote must match a whole number in the source: "1.2" does
not match inside "41.2", and "4.1" does not match inside "4.15".

Results per claim:
  PASS         the quote is on the page you gave
  WRONG PAGE   the quote is in the source, but on other page(s): fix the page
  OTHER ROW    a table cell you quoted after a row label is on another line
  NOT FOUND    the quote is not in the source: copy it again or change the verdict
  NO QUOTE     a supported or contradicted claim needs a quote
  NO SEARCH    a not_in_source claim needs the terms you searched for
  BAD VERDICT  the verdict is not one of the four
  OK           nothing more to check
Any of these can carry a note that searched terms do appear. Read those
passages; the note does not change the exit code.

The exit code is 1 when any claim is WRONG PAGE, OTHER ROW, NOT FOUND,
NO QUOTE, NO SEARCH or BAD VERDICT, and 0 otherwise.
"""

import json
import os
import re
import sys
import unicodedata

# Keep the skill folder unchanged: no __pycache__ next to the scripts.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import load_pages, term_pattern  # noqa: E402

TRANSLATE = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
    "―": "-", "−": "-", "­": None, "…": "...",
})
SEPARATOR = re.compile(r"\s*(?:\[(?:\.\.\.|…)\]|\.\.\.|…)\s*")
VERDICTS = {
    "supported": "supported",
    "contradicted": "contradicted",
    "not_in_source": "not_in_source",
    "not_in_the_source": "not_in_source",
    "notinsource": "not_in_source",
    "cant_check": "cant_check",
    "can_t_check": "cant_check",
    "cannot_check": "cant_check",
    "cantcheck": "cant_check",
}
BLOCKING = ("WRONG PAGE", "OTHER ROW", "NOT FOUND", "NO QUOTE", "NO SEARCH", "BAD VERDICT")


def normalize(text):
    text = unicodedata.normalize("NFKC", text).translate(TRANSLATE)
    return re.sub(r"\s+", " ", text).strip().casefold()


def variants(text):
    """The page text as written, and with end-of-line hyphenation undone."""
    joined = re.sub(r"(\w)-[ \t]*\n\s*(\w)", r"\1\2", text)
    return [normalize(text), normalize(joined)]


def squeeze(text):
    """Drop spaces, except between two digits, so numbers stay apart."""
    return re.sub(r"(?<!\d) | (?!\d)", "", text)


def digit_edges_ok(haystack, start, end):
    """A match that starts or ends with a digit must not cut a number."""
    if haystack[start].isdigit() and start > 0:
        before = haystack[start - 1]
        if before.isdigit():
            return False
        if before in ".," and start > 1 and haystack[start - 2].isdigit():
            return False
    if haystack[end - 1].isdigit() and end < len(haystack):
        after = haystack[end]
        if after.isdigit():
            return False
        if after in ".," and end + 1 < len(haystack) and haystack[end + 1].isdigit():
            return False
    return True


def find_piece(piece, haystack, position):
    """Index just past the first acceptable match at or after position, or -1."""
    found = haystack.find(piece, position)
    while found >= 0:
        end = found + len(piece)
        if digit_edges_ok(haystack, found, end):
            return end
        found = haystack.find(piece, found + 1)
    return -1


def pieces_in_order(pieces, haystack):
    position = 0
    for piece in pieces:
        position = find_piece(piece, haystack, position)
        if position < 0:
            return False
    return True


def quote_in(pieces, text_variants):
    """Return '' if found, ' (ignoring spaces)' if found only that way, None if not."""
    for text in text_variants:
        if pieces_in_order(pieces, text):
            return ""
    squeezed = [squeeze(piece) for piece in pieces]
    for text in text_variants:
        if pieces_in_order(squeezed, squeeze(text)):
            return " (ignoring spaces)"
    return None


def parse_pages(value):
    if value is None or value == "":
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(parse_pages(item))
        return result
    numbers = [int(n) for n in re.findall(r"\d+", str(value))]
    if re.search(r"\d\s*[-–]\s*\d", str(value)) and len(numbers) == 2:
        low, high = numbers
        return list(range(low, high + 1)) if high >= low else numbers
    return numbers


def parse_verdict(value):
    key = re.sub(r"[^a-z]+", "_", str(value).lower()).strip("_")
    return VERDICTS.get(key, VERDICTS.get(key.replace("_", ""), key))


def searched_hits(terms, by_number):
    hits = []
    for term in terms:
        pattern = term_pattern(term, False)
        found = [n for n, text in by_number.items() if pattern.search(text)]
        if found:
            hits.append(f'"{term}" on p. {", ".join(map(str, found[:10]))}')
    return hits


NUMERIC_PIECE = re.compile(r"^[\d\s.,%$()+-]+$")


def row_label_ok(pieces, text):
    """Table cells quoted after a row label must sit on that label's line."""
    label = None
    run = []
    for piece in pieces:
        if NUMERIC_PIECE.match(piece) and label is not None:
            run.append(piece)
            lines = [normalize(line) for line in text.split("\n")]
            if not any(pieces_in_order([label] + run, line) for line in lines):
                return label, piece
        else:
            label, run = piece, []
    return None


def check_quote(quote, cited, by_number, page_variants, split_row=False):
    """Return (status, detail) for one quote."""
    pieces = [normalize(p) for p in SEPARATOR.split(quote) if normalize(p)]
    detail = "quote is long; keep the words that prove the point. " if len(quote.split()) > 60 else ""
    missing_pages = [n for n in cited if n not in page_variants]
    if missing_pages:
        detail += (f"p. {', '.join(map(str, missing_pages))} doesn't exist "
                   f"(the source has {len(by_number)} pages). ")
    span = [n for n in cited if n in page_variants]
    if span:
        text = "\n".join(by_number[n] for n in span)
        how = quote_in(pieces, variants(text))
        if how is not None:
            alone = [n for n in span if quote_in(pieces, page_variants[n]) is not None]
            if len(cited) > 1 and alone:
                return "WRONG PAGE", detail + (
                    f"the whole quote is on p. {', '.join(map(str, alone))}: cite only that page"
                )
            off_row = None if split_row else row_label_ok(pieces, text)
            if off_row:
                label, cell = off_row
                return "OTHER ROW", detail + (
                    f'"{cell}" is not on the same line as "{label}", so it is probably '
                    "from another row. Quote the cells of the row you mean. If the "
                    'extraction really splits this row over two lines, add "split_row": true'
                )
            return "PASS", detail + f"p. {', '.join(map(str, cited))}{how}"
    elsewhere = [n for n in by_number if quote_in(pieces, page_variants[n]) is not None]
    if elsewhere:
        return "WRONG PAGE", detail + (
            f"cited p. {', '.join(map(str, cited)) or 'none'}, "
            f"found on p. {', '.join(map(str, elsewhere))}"
        )
    missing = [p for p in pieces
               if not any(quote_in([p], v) is not None for v in page_variants.values())]
    if missing:
        hint = ""
        if re.search(r"\d", missing[0]):
            hint = (". Numbers must be copied exactly, with the source's thousands "
                    "separators, and can't be part of a longer number")
        return "NOT FOUND", detail + f'not in the source: "{missing[0][:80]}"{hint}'
    return "NOT FOUND", detail + (
        "each piece is in the source, but not together on the cited page(s) in this "
        "order. If the quote runs across a page break, cite a range such as 1-2"
    )


def main():
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    pages = load_pages(sys.argv[1])
    with open(sys.argv[2], encoding="utf-8") as handle:
        data = json.load(handle)
    claims = data["claims"] if isinstance(data, dict) else data

    by_number = {number: "\n".join(lines) for number, _, lines in pages}
    page_variants = {number: variants(text) for number, text in by_number.items()}

    counts = {}
    for position, claim in enumerate(claims, start=1):
        claim_id = claim.get("id", position)
        verdict = parse_verdict(claim.get("verdict", ""))
        quote = (claim.get("quote") or "").strip()
        cited = parse_pages(claim.get("page"))
        searched = claim.get("searched") or []
        if isinstance(searched, str):
            searched = [searched]
        notes = []

        if verdict not in VERDICTS.values():
            status = "BAD VERDICT"
            notes.append(f'"{claim.get("verdict", "")}" is not supported, contradicted, '
                         "not_in_source or cant_check. Split a partly supported claim")
        elif quote:
            status, detail = check_quote(quote, cited, by_number, page_variants,
                                         bool(claim.get("split_row")))
            notes.append(detail)
        elif verdict in ("supported", "contradicted"):
            status = "NO QUOTE"
            notes.append(f"a {verdict} claim needs a quote from the source")
        else:
            status = "OK"

        if verdict == "not_in_source":
            if not searched:
                if status not in BLOCKING:
                    status = "NO SEARCH"
                notes.append('add "searched": the words and numbers you looked for')
            else:
                hits = searched_hits(searched, by_number)
                if hits:
                    notes.append("searched terms appear: " + "; ".join(hits) +
                                 ". Keep not_in_source only if none of those passages makes the claim")
                else:
                    notes.append("no searched term appears in the source")

        counts[status] = counts.get(status, 0) + 1
        line = f"#{claim_id} {status}"
        if verdict:
            line += f" [{verdict}]"
        notes = [note for note in notes if note]
        if notes:
            line += ": " + ". ".join(notes)
        print(line)

    summary = ", ".join(f"{count} {status}" for status, count in counts.items())
    print(f"\n{len(claims)} claim(s): {summary}")
    failed = any(status in BLOCKING for status in counts)
    if failed:
        print("Fix every " + ", ".join(s for s in BLOCKING if s in counts) +
              " line before you report the table.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
