#!/usr/bin/env python3
"""Find where terms appear in a pages file, with the page number.

    python3 search.py report.pages.txt "U-6" "7.6" "leisure and hospitality"

Each term is matched without regard to case, across line breaks and words
split by a hyphen at the end of a line. A term that is a number also
matches it with or without thousands separators and never inside a longer
number: "40367" finds "40,367" but not "140,367"; "7.6" finds "7.6" and
"7.6%" but not "17.6" or "7.65". Use --regex to pass a regular expression.

For every hit it prints the page and the line, with the lines around it
when you ask for --context.
"""

import argparse
import re
import sys

PAGE_MARKER = re.compile(r"^=== Page (\d+)(?: \(printed: ([^)]*)\))? ===$")
NUMBER = re.compile(r"^[-+]?[\d,]*\d(?:\.\d+)?$")
HYPHEN_BREAK = r"(?:-[ \t]*\n[ \t]*)?"


def load_pages(path):
    """Return a list of (page number, printed label, list of lines)."""
    pages = []
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            marker = PAGE_MARKER.match(line)
            if marker:
                pages.append((int(marker.group(1)), marker.group(2), []))
            elif pages:
                pages[-1][2].append(line)
    if not pages:
        sys.exit(f"No '=== Page N ===' markers in {path}. Run extract_pages.py first.")
    return pages


def number_pattern(term):
    sign = ""
    if term[0] in "+-":
        sign, term = re.escape(term[0]), term[1:]
    whole, _, fraction = term.replace(",", "").partition(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    body = r"[,\s]?".join(groups)
    if fraction:
        body += r"\." + fraction
    return rf"(?<![\d.,]){sign}{body}(?!\d|[.,]\d)"


def term_pattern(term, as_regex):
    if as_regex:
        return re.compile(term, re.IGNORECASE)
    if NUMBER.match(term):
        return re.compile(number_pattern(term))
    return re.compile(r"\s+".join(word_pattern(word) for word in term.split()), re.IGNORECASE)


def word_pattern(word):
    """A word that may be split by a hyphen at the end of a line."""
    pieces = [re.escape(char) for char in word]
    out = pieces[0]
    for before, char in zip(word, pieces[1:]):
        out += (HYPHEN_BREAK if before.isalnum() else "") + char
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pages_file", help="output of extract_pages.py")
    parser.add_argument("terms", nargs="+", help="words, phrases or numbers")
    parser.add_argument("--regex", action="store_true", help="terms are regular expressions")
    parser.add_argument("-C", "--context", type=int, default=0, help="lines to show around each hit")
    parser.add_argument("--max", type=int, default=15, help="hits to show per term (default 15)")
    args = parser.parse_args()

    pages = load_pages(args.pages_file)
    for term in args.terms:
        pattern = term_pattern(term, args.regex)
        hits = []
        for number, label, lines in pages:
            text = "\n".join(lines)
            seen = set()
            for match in pattern.finditer(text):
                first = text.count("\n", 0, match.start())
                last = text.count("\n", 0, match.end())
                if first not in seen:
                    seen.add(first)
                    hits.append((number, label, lines, first, last))
        on_pages = sorted({hit[0] for hit in hits})
        page_list = ", ".join(str(n) for n in on_pages[:30])
        if len(on_pages) > 30:
            page_list += ", ..."
        print(f'## "{term}": {len(hits)} hit(s)' + (f" on page(s) {page_list}" if hits else ""))
        for number, label, lines, first, last in hits[: args.max]:
            where = f"p. {number}" + (f" (printed {label})" if label else "")
            start = max(0, first - args.context)
            end = min(len(lines), last + args.context + 1)
            for i in range(start, end):
                mark = ">" if first <= i <= last else " "
                print(f"{mark} {where}: {lines[i].strip()}")
            if args.context:
                print()
        if len(hits) > args.max:
            print(f"  ... {len(hits) - args.max} more. Narrow the term or raise --max.")
        print()


if __name__ == "__main__":
    main()
