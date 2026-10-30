"""
Markdown chunking for the product-management knowledge base.

Knowledge documents carry YAML-ish frontmatter and are organized under `##`
headings. Each heading becomes one chunk, prefixed with a
`Document > Section` breadcrumb so both lexical and dense retrieval see the
document context even when a section is read in isolation.

Frontmatter is parsed by hand rather than with PyYAML: the format is a fixed,
tiny subset (scalars plus inline lists) and the serverless bundle stays smaller
without the dependency.

User-uploaded documents go through `chunk_sections` instead: they have no
authored structure to rely on, so they are split on the most natural boundary
that fits (paragraph, line, sentence, word) into smaller, overlapping passages.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

# Sized so a typical authored `##` section survives as a single chunk. Splitting
# a coherent section mid-argument produces fragments that rank on stray keywords
# without carrying the reasoning that made the section useful.
MAX_CHUNK_CHARS = 2400
CHUNK_OVERLAP_CHARS = 200
MIN_CHUNK_CHARS = 80
# Uploads keep much shorter passages than the curated corpus: a slide or a
# short PDF page can carry one decisive fact, and the user chose to supply it.
# Only fragments too small to state anything ("Thank you", a page number) go.
MIN_UPLOAD_PASSAGE_CHARS = 20

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class Chunk:
    id: str
    doc_id: str
    title: str
    heading: str
    text: str
    domain: str = "general"
    authority: str = "practice"
    tags: List[str] = field(default_factory=list)
    #: "corpus" for the curated knowledge base, "upload" for a user's document.
    source: str = "corpus"

    @property
    def embedding_text(self) -> str:
        """What gets embedded/indexed: breadcrumb plus body."""
        return f"{self.title} > {self.heading}\n\n{self.text}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "title": self.title,
            "heading": self.heading,
            "text": self.text,
            "domain": self.domain,
            "authority": self.authority,
            "tags": self.tags,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        return cls(
            id=data["id"],
            doc_id=data["doc_id"],
            title=data.get("title", ""),
            heading=data.get("heading", ""),
            text=data.get("text", ""),
            domain=data.get("domain", "general"),
            authority=data.get("authority", "practice"),
            tags=list(data.get("tags") or []),
            source=data.get("source") or "corpus",
        )


def parse_frontmatter(raw: str) -> tuple[Dict[str, Any], str]:
    """Split `---` frontmatter from the markdown body."""
    match = _FRONTMATTER.match(raw)
    if not match:
        return {}, raw

    meta: Dict[str, Any] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [
                item.strip().strip("'\"")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            meta[key] = value.strip("'\"")
    return meta, raw[match.end():]


def _split_long_section(text: str) -> List[str]:
    """Split an oversized section on paragraph boundaries, with overlap."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    parts: List[str] = []
    buffer = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= MAX_CHUNK_CHARS:
            buffer = candidate
            continue
        if buffer:
            parts.append(buffer)
            tail = buffer[-CHUNK_OVERLAP_CHARS:]
            buffer = f"{tail}\n\n{paragraph}".strip()
        else:
            # A single paragraph longer than the cap: hard-wrap it.
            for start in range(0, len(paragraph), MAX_CHUNK_CHARS - CHUNK_OVERLAP_CHARS):
                parts.append(paragraph[start : start + MAX_CHUNK_CHARS])
            buffer = ""
    if buffer:
        parts.append(buffer)
    return parts


def chunk_markdown(raw: str, *, fallback_doc_id: str) -> List[Chunk]:
    """Turn one knowledge document into retrievable chunks."""
    meta, body = parse_frontmatter(raw)

    doc_id = str(meta.get("doc_id") or fallback_doc_id)
    title = str(meta.get("title") or doc_id.replace("-", " ").title())
    domain = str(meta.get("domain") or "general")
    authority = str(meta.get("authority") or "practice")
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

    chunks: List[Chunk] = []
    for heading, section_text in markdown_sections(body):
        if len(section_text) < MIN_CHUNK_CHARS:
            continue
        for part_index, part in enumerate(_split_long_section(section_text)):
            digest = hashlib.sha1(
                f"{doc_id}|{heading}|{part_index}".encode("utf-8")
            ).hexdigest()[:10]
            chunks.append(
                Chunk(
                    id=f"{doc_id}#{digest}",
                    doc_id=doc_id,
                    title=title,
                    heading=heading if part_index == 0 else f"{heading} (cont. {part_index + 1})",
                    text=part.strip(),
                    domain=domain,
                    authority=authority,
                    tags=list(tags),
                )
            )
    return chunks


def markdown_sections(body: str, heading: re.Pattern = _HEADING) -> List[tuple[str, str]]:
    """Split a markdown body into `(heading, text)` pairs on `heading` matches."""
    headings = list(heading.finditer(body))
    sections: List[tuple[str, str]] = []

    if not headings:
        sections.append(("Overview", body.strip()))
    else:
        preamble = body[: headings[0].start()].strip()
        # Drop the leading `# Title` line; it duplicates the frontmatter title.
        preamble = re.sub(r"^#\s+.*$", "", preamble, count=1, flags=re.MULTILINE).strip()
        if len(preamble) >= MIN_CHUNK_CHARS:
            sections.append(("Overview", preamble))
        for index, match in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
            sections.append((match.group(1).strip(), body[match.end() : end].strip()))
    return sections


# Coarsest first: a passage should break between paragraphs when it can, and
# only fall back to lines, sentences, then words when a unit is still too long.
_SEPARATORS = ("\n\n", "\n", ". ", " ")


def _atomize(text: str, max_chars: int, level: int = 0) -> List[str]:
    """Break text into pieces no longer than `max_chars`, separators kept."""
    if len(text) <= max_chars:
        return [text]
    if level >= len(_SEPARATORS):
        return [text[start : start + max_chars] for start in range(0, len(text), max_chars)]

    separator = _SEPARATORS[level]
    parts = text.split(separator)
    pieces: List[str] = []
    for index, part in enumerate(parts):
        piece = part + separator if index < len(parts) - 1 else part
        if piece:
            pieces.extend(_atomize(piece, max_chars, level + 1))
    return pieces


def split_text(text: str, max_chars: int, overlap: int) -> List[str]:
    """Pack text into passages of at most `max_chars`, each carrying up to
    `overlap` characters of the previous one so a fact straddling a boundary is
    still retrievable from either side."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    passages: List[str] = []
    buffer = ""
    for piece in _atomize(text, max_chars):
        if len(buffer) + len(piece) <= max_chars:
            buffer += piece
            continue
        if buffer.strip():
            passages.append(buffer.strip())
        tail = buffer[-overlap:] if overlap else ""
        # Start the carried-over tail on a word boundary.
        tail = tail[tail.find(" ") + 1 :] if " " in tail else ""
        buffer = tail + piece if len(tail) + len(piece) <= max_chars else piece
    if buffer.strip():
        passages.append(buffer.strip())
    return passages


def chunk_sections(
    sections: List[tuple[str, str]],
    *,
    doc_id: str,
    title: str,
    max_chars: int,
    overlap: int,
    domain: str = "uploaded",
    authority: str = "user",
    source: str = "upload",
) -> List[Chunk]:
    """Chunk pre-split `(label, text)` sections of an uploaded document.

    A section with no label (plain text) is numbered by position, so a citation
    still points somewhere a reader can find: "Part 4", "Page 12".
    """
    chunks: List[Chunk] = []
    part_number = 0
    for label, section_text in sections:
        for index, passage in enumerate(split_text(section_text, max_chars, overlap)):
            if len(passage) < MIN_UPLOAD_PASSAGE_CHARS:
                continue
            part_number += 1
            if label:
                heading = label if index == 0 else f"{label} (cont. {index + 1})"
            else:
                heading = f"Part {part_number}"
            chunks.append(
                Chunk(
                    id=f"{doc_id}#{len(chunks) + 1}",
                    doc_id=doc_id,
                    title=title,
                    heading=heading,
                    text=passage,
                    domain=domain,
                    authority=authority,
                    source=source,
                )
            )
    return chunks


def load_knowledge_dir(directory: Path) -> List[Chunk]:
    """Chunk every `.md` file in a knowledge directory."""
    chunks: List[Chunk] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        chunks.extend(chunk_markdown(raw, fallback_doc_id=path.stem))
    return chunks
