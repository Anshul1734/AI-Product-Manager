"""
Markdown chunking for the product-management knowledge base.

Knowledge documents carry YAML-ish frontmatter and are organized under `##`
headings. Each heading becomes one chunk, prefixed with a
`Document > Section` breadcrumb so both lexical and dense retrieval see the
document context even when a section is read in isolation.

Frontmatter is parsed by hand rather than with PyYAML: the format is a fixed,
tiny subset (scalars plus inline lists) and the serverless bundle stays smaller
without the dependency.
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

    headings = list(_HEADING.finditer(body))
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

    chunks: List[Chunk] = []
    for heading, section_text in sections:
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


def load_knowledge_dir(directory: Path) -> List[Chunk]:
    """Chunk every `.md` file in a knowledge directory."""
    chunks: List[Chunk] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        chunks.extend(chunk_markdown(raw, fallback_doc_id=path.stem))
    return chunks
