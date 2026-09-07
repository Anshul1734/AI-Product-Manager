"""
Long-term plan memory.

Stores every completed run so later runs can recall genuinely similar past work.
Recall reuses the BM25 scorer from the retrieval layer rather than the raw
word-overlap ratio this project used previously -- overlap treats every term as
equally informative, so two unrelated ideas that both say "app for users" scored
as similar while "RICE" and "prioritization" counted for nothing.

Persistence is a JSON file under `settings.data_dir`. On serverless that
resolves to /tmp, which is per-instance and ephemeral: memory survives warm
invocations but not a cold start. Point MEMORY at a real database before relying
on it for anything durable.
"""
from __future__ import annotations

import json
import math
import threading
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from ..rag.store import tokenize


@dataclass
class MemoryEntry:
    entry_id: str
    thread_id: str
    created_at: datetime
    idea: str
    product_name: str
    problem_statement: str
    quality_score: Optional[float] = None
    tech_stack: List[str] = field(default_factory=list)
    top_features: List[str] = field(default_factory=list)
    target_users: List[str] = field(default_factory=list)

    @property
    def search_text(self) -> str:
        return " ".join(
            [
                self.idea,
                self.product_name,
                self.problem_statement,
                " ".join(self.top_features),
                " ".join(self.target_users),
                " ".join(self.tech_stack),
            ]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "thread_id": self.thread_id,
            "created_at": self.created_at.isoformat(),
            "idea": self.idea,
            "product_name": self.product_name,
            "problem_statement": self.problem_statement,
            "quality_score": self.quality_score,
            "tech_stack": self.tech_stack,
            "top_features": self.top_features,
            "target_users": self.target_users,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        raw_date = data.get("created_at")
        try:
            created = datetime.fromisoformat(raw_date) if raw_date else datetime.now(timezone.utc)
        except ValueError:
            created = datetime.now(timezone.utc)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return cls(
            entry_id=data.get("entry_id") or "",
            thread_id=data.get("thread_id") or "",
            created_at=created,
            idea=data.get("idea") or "",
            product_name=data.get("product_name") or "",
            problem_statement=data.get("problem_statement") or "",
            quality_score=data.get("quality_score"),
            tech_stack=list(data.get("tech_stack") or []),
            top_features=list(data.get("top_features") or []),
            target_users=list(data.get("target_users") or []),
        )


class PlanMemory:
    """Thread-safe, file-backed store of past product plans."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or (settings.data_dir / "plan_memory.json")
        self._lock = threading.RLock()
        self._entries: List[MemoryEntry] = []
        self._load()

    # -------------------------------------------------------------- writes

    def record(self, entry: MemoryEntry) -> None:
        if not settings.MEMORY_ENABLED:
            return
        with self._lock:
            self._entries.append(entry)
            self._prune_locked()
            self._save_locked()

    def _prune_locked(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.MEMORY_MAX_AGE_DAYS)
        self._entries = [entry for entry in self._entries if entry.created_at > cutoff]

        per_thread: Counter = Counter()
        kept: List[MemoryEntry] = []
        for entry in reversed(self._entries):
            if per_thread[entry.thread_id] >= settings.MEMORY_MAX_ENTRIES_PER_THREAD:
                continue
            per_thread[entry.thread_id] += 1
            kept.append(entry)
        self._entries = list(reversed(kept))

    # --------------------------------------------------------------- reads

    def thread_history(self, thread_id: str, limit: int = 3) -> List[MemoryEntry]:
        with self._lock:
            matches = [entry for entry in self._entries if entry.thread_id == thread_id]
            return matches[-limit:]

    def search(self, query: str, k: int = 3, exclude_thread: Optional[str] = None) -> List[Tuple[MemoryEntry, float]]:
        """BM25 recall over stored plans."""
        with self._lock:
            corpus = [
                entry
                for entry in self._entries
                if exclude_thread is None or entry.thread_id != exclude_thread
            ]

        query_terms = tokenize(query)
        if not corpus or not query_terms:
            return []

        tokenized = [tokenize(entry.search_text) for entry in corpus]
        frequencies = [Counter(tokens) for tokens in tokenized]
        lengths = [len(tokens) or 1 for tokens in tokenized]
        avg_length = sum(lengths) / len(lengths)

        document_frequency: Counter = Counter()
        for tokens in tokenized:
            for term in set(tokens):
                document_frequency[term] += 1

        k1, b = 1.5, 0.75
        total = len(corpus)
        scored: List[Tuple[MemoryEntry, float]] = []

        for index, entry in enumerate(corpus):
            score = 0.0
            for term in query_terms:
                tf = frequencies[index].get(term, 0)
                if tf == 0:
                    continue
                df = document_frequency[term]
                idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
                score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * lengths[index] / avg_length))
            if score > 0:
                scored.append((entry, round(score, 4)))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:k]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            scores = [entry.quality_score for entry in self._entries if entry.quality_score is not None]
            threads = {entry.thread_id for entry in self._entries}
            return {
                "total_entries": len(self._entries),
                "total_threads": len(threads),
                "average_quality": round(sum(scores) / len(scores), 2) if scores else None,
                "storage_path": str(self.path),
                "ephemeral": settings.is_serverless,
            }

    def clear(self) -> int:
        with self._lock:
            removed = len(self._entries)
            self._entries = []
            self._save_locked()
            return removed

    # --------------------------------------------------------- persistence

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._entries = [MemoryEntry.from_dict(item) for item in data.get("entries") or []]
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            app_logger.warning("Could not load plan memory; starting empty", error=str(exc)[:200])
            self._entries = []

    def _save_locked(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "entries": [entry.to_dict() for entry in self._entries],
            }
            self.path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            app_logger.warning("Could not persist plan memory", error=str(exc)[:200])


_memory: Optional[PlanMemory] = None
_memory_lock = threading.Lock()


def get_memory() -> PlanMemory:
    global _memory
    if _memory is None:
        with _memory_lock:
            if _memory is None:
                _memory = PlanMemory()
    return _memory
