"""
Text extraction for uploaded documents.

Each parser returns `(label, text)` sections rather than one flat string, so
provenance survives into citations: a PDF passage cites its page, a markdown or
Word passage cites its heading.

The PDF and Word libraries are imported lazily. They are only needed while an
upload is being processed, and keeping them off the import path keeps the
resident footprint of the API down on small instances.
"""
from __future__ import annotations

import io
import re
from pathlib import PurePath
from typing import Callable, Dict, List, Tuple

from .chunking import markdown_sections

Sections = List[Tuple[str, str]]

# Any markdown heading level counts in uploaded files; the curated corpus's
# `##`-only convention is not something arbitrary documents follow.
_ANY_HEADING = re.compile(r"^#{1,4}\s+(.+?)\s*#*\s*$", re.MULTILINE)


class UnsupportedDocument(ValueError):
    """The file cannot be turned into text."""


def _decode(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Legacy Windows exports. cp1252 maps nearly every byte, so this always
        # yields something readable.
        return data.decode("cp1252", errors="replace")


def _plain(data: bytes) -> Sections:
    return [("", _decode(data))]


def _markdown(data: bytes) -> Sections:
    text = _decode(data)
    # Strip YAML frontmatter if present; it is metadata, not content.
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    if not _ANY_HEADING.search(text):
        return [("", text)]
    return markdown_sections(text, _ANY_HEADING)


def _pdf(data: bytes) -> Sections:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise UnsupportedDocument("PDF support is not installed (pip install pypdf)") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise UnsupportedDocument("This PDF is password-protected.")
        sections: Sections = []
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                sections.append((f"Page {number}", text))
        return sections
    except PdfReadError as exc:
        raise UnsupportedDocument(f"Could not read this PDF: {exc}") from exc


def _docx(data: bytes) -> Sections:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise UnsupportedDocument("Word support is not installed (pip install python-docx)") from exc

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise UnsupportedDocument(f"Could not read this Word document: {exc}") from exc

    # Rebuild a markdown skeleton from paragraph styles, so Word headings split
    # sections exactly as markdown headings do.
    lines: List[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = (paragraph.style.name or "").lower() if paragraph.style is not None else ""
        if style.startswith("heading") or style == "title":
            lines.append(f"\n## {text}\n")
        else:
            lines.append(text + "\n")
    for table in document.tables:
        rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
        if rows:
            lines.append("\n" + "\n".join(rows) + "\n")

    return _markdown("\n".join(lines).encode("utf-8"))


_PARSERS: Dict[str, Callable[[bytes], Sections]] = {
    ".txt": _plain,
    ".text": _plain,
    ".csv": _plain,
    ".tsv": _plain,
    ".json": _plain,
    ".log": _plain,
    ".rst": _plain,
    ".md": _markdown,
    ".markdown": _markdown,
    ".pdf": _pdf,
    ".docx": _docx,
}

SUPPORTED_EXTENSIONS = tuple(sorted(_PARSERS))


def extract_sections(filename: str, data: bytes) -> Sections:
    """Turn an uploaded file into labelled text sections."""
    suffix = PurePath(filename or "").suffix.lower()
    parser = _PARSERS.get(suffix)
    if parser is None:
        raise UnsupportedDocument(
            f"Unsupported file type '{suffix or filename}'. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    sections = [(label, text.strip()) for label, text in parser(data) if text and text.strip()]
    if sum(len(text) for _, text in sections) < 20:
        hint = " A scanned PDF has no text layer; run OCR on it first." if suffix == ".pdf" else ""
        raise UnsupportedDocument(f"No readable text found in this file.{hint}")
    return sections
