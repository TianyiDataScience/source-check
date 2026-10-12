#!/usr/bin/env python3
"""Extract a document's text with a marker line before every page.

    python3 extract_pages.py report.pdf -o report.pages.txt

Output looks like this:

    === Page 1 ===
    ...text of the first page...
    === Page 2 (printed: ii) ===
    ...

Page numbers are the PDF viewer's: page 1 is the first page of the file.
When the PDF defines its own page labels and they differ, the label is
shown as "printed".

PDF text comes from the first backend that works: poppler's pdftotext,
then pypdf, pdfplumber or PyMuPDF if one of them is installed. .txt, .md,
.html and .docx files need nothing beyond Python 3.8. Their text has no
pages, so it is written as a single "Page 1".

A summary goes to stderr: pages, characters, the backend used, and the
pages with almost no text (usually scanned images that need OCR).
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import zipfile
from html.parser import HTMLParser

LOW_TEXT_CHARS = 40


def pdf_pdftotext(path):
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    result = subprocess.run(
        [exe, "-layout", "-enc", "UTF-8", path, "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    text = result.stdout.decode("utf-8", errors="replace")
    pages = text.split("\f")
    # pdftotext ends the last page with a form feed too.
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def pdf_pypdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text(extraction_mode="layout") or "")
        except TypeError:
            # pypdf before 3.17 has no layout mode.
            pages.append(page.extract_text() or "")
    return pages


def pdf_pdfplumber(path):
    try:
        import pdfplumber
    except ImportError:
        return None
    with pdfplumber.open(path) as pdf:
        return [page.extract_text(layout=True) or "" for page in pdf.pages]


def pdf_pymupdf(path):
    try:
        import fitz
    except ImportError:
        return None
    with fitz.open(path) as doc:
        return [page.get_text() for page in doc]


PDF_BACKENDS = [
    ("pdftotext", pdf_pdftotext),
    ("pypdf", pdf_pypdf),
    ("pdfplumber", pdf_pdfplumber),
    ("pymupdf", pdf_pymupdf),
]


def pdf_page_labels(path, count):
    """Printed page labels, when pypdf is available and the PDF has them."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        labels = list(PdfReader(path).page_labels)
    except Exception:
        return None
    if len(labels) != count:
        return None
    if all(label == str(i + 1) for i, label in enumerate(labels)):
        return None
    return labels


class _TextFromHTML(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
             "table", "section", "article", "header", "footer", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append("  ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_text(raw):
    parser = _TextFromHTML()
    parser.feed(raw)
    text = "".join(parser.parts)
    return re.sub(r"\n{3,}", "\n\n", text)


def docx_text(path):
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return html.unescape(text)


def extract(path):
    """Return (pages, backend, labels)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        for name, backend in PDF_BACKENDS:
            try:
                pages = backend(path)
            except Exception as error:  # a broken backend should not stop the next one
                print(f"{name} failed: {error}", file=sys.stderr)
                pages = None
            if pages:
                return pages, name, pdf_page_labels(path, len(pages))
        sys.exit(
            "No PDF text extractor found. Install one of them:\n"
            "  macOS:   brew install poppler      (gives pdftotext)\n"
            "  Linux:   sudo apt install poppler-utils\n"
            "  Any OS:  python3 -m pip install pypdf"
        )
    with open(path, "rb") as handle:
        raw_bytes = handle.read()
    if ext == ".docx":
        return [docx_text(path)], "docx", None
    raw = raw_bytes.decode("utf-8", errors="replace")
    if ext in (".html", ".htm"):
        return [html_text(raw)], "html", None
    return [raw], "text", None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", help="PDF, .txt, .md, .html or .docx file")
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    args = parser.parse_args()

    if not os.path.isfile(args.source):
        sys.exit(f"File not found: {args.source}")

    pages, backend, labels = extract(args.source)

    chunks = []
    low_text = []
    for index, text in enumerate(pages):
        number = index + 1
        header = f"=== Page {number} ==="
        if labels and labels[index] != str(number):
            header = f"=== Page {number} (printed: {labels[index]}) ==="
        chunks.append(header + "\n" + text.rstrip() + "\n")
        if len(text.strip()) < LOW_TEXT_CHARS:
            low_text.append(number)
    output = "\n".join(chunks)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
    else:
        sys.stdout.write(output)

    characters = sum(len(page) for page in pages)
    print(
        f"{len(pages)} page(s), {characters:,} characters, extracted with {backend}.",
        file=sys.stderr,
    )
    if low_text:
        shown = ", ".join(str(n) for n in low_text[:20])
        more = "" if len(low_text) <= 20 else f" and {len(low_text) - 20} more"
        print(
            f"Pages with almost no text (scanned or image-only?): {shown}{more}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
