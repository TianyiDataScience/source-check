#!/usr/bin/env python3
"""Write examples/water-report.pdf, a small fictional report for tests and demos.

It needs nothing beyond Python. The PDF has three pages, a word split
across a line break, curly quotes, an en dash, and a table where the
seasonally adjusted and unadjusted totals differ, which is the trap most AI
summaries fall into. The tests also build a copy with printed page labels
i, 1 and 2.
"""

import os

PAGES = [
    [
        (72, 700, 20, "Riverside Water Authority"),
        (72, 672, 14, "Quarterly Report – Third Quarter 2026"),
        (72, 630, 10, "This is a fictional document, written to test the source-check skill."),
        (72, 616, 10, "Every number in it is made up."),
    ],
    [
        (72, 720, 12, "1. Demand"),
        (72, 696, 10, "Average daily demand was 41.2 million gallons in September 2026,"),
        (72, 682, 10, "seasonally adjusted, up from 39.8 million gallons in August. Before"),
        (72, 668, 10, "seasonal adjustment, September demand was 42.9 million gallons. Most"),
        (72, 654, 10, "of the increase came from the residen-"),
        (72, 640, 10, "tial and industrial classes (Table 2)."),
        (72, 612, 12, "2. Rates and outlook"),
        (72, 588, 10, "The Board left the base rate at $4.15 per 1,000 gallons."),
        (72, 574, 10, "“We expect no rate change before the spring review,” said Director Ana Ruiz."),
        (72, 560, 10, "The Authority does not publish demand forecasts in this report."),
    ],
    [
        (72, 720, 12, "Table 2. Water use by customer class, million gallons per day"),
        (72, 696, 9, "                       Seasonally adjusted          Not seasonally adjusted"),
        (72, 684, 9, "Customer class         Aug. 2026     Sept. 2026     Sept. 2026"),
        (72, 668, 9, "Residential                 22.4           22.9           24.1"),
        (72, 656, 9, "Commercial                  11.0           11.3           12.0"),
        (72, 644, 9, "Industrial                   6.4            7.0            6.8"),
        (72, 632, 9, "Total                       39.8           41.2           42.9"),
        (72, 608, 9, "Figures for September are preliminary."),
    ],
]


def escape(text):
    raw = text.encode("cp1252")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def content_stream(lines):
    parts = []
    for x, y, size, text in lines:
        font = b"/F2" if " " * 3 in text else b"/F1"
        parts.append(b"BT %s %d Tf %d %d Td (%s) Tj ET" % (font, size, x, y, escape(text)))
    return b"\n".join(parts)


def build(page_labels=False):
    objects = []

    def add(body):
        objects.append(body)
        return len(objects)

    font_regular = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_mono = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")
    pages_id = len(objects) + 1 + 2 * len(PAGES)
    page_ids = []
    for lines in PAGES:
        stream = content_stream(lines)
        content_id = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        page_ids.append(add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>"
            % (pages_id, font_regular, font_mono, content_id)
        ))
    kids = b" ".join(b"%d 0 R" % page for page in page_ids)
    assert add(b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids))) == pages_id
    labels = b"/PageLabels << /Nums [0 << /S /r >> 1 << /S /D >>] >> " if page_labels else b""
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R %s>>" % (pages_id, labels))
    info = add(b"<< /Title (Riverside Water Authority, Quarterly Report Q3 2026 \\(fictional\\)) >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += (b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, catalog, info, xref))
    return bytes(out)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "..", "examples", "water-report.pdf")
    with open(target, "wb") as handle:
        handle.write(build())
    print(os.path.normpath(target))
