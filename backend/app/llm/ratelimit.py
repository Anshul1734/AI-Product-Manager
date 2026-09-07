"""
Client-side token pacing.

Groq enforces a tokens-per-minute budget per model, and on the free tier that
budget (8,000 TPM) is smaller than one full pipeline run. Exceeding it does not
return 429 -- it returns **HTTP 413 with `code: rate_limit_exceeded`**, which is
easy to misread as an oversized payload. (This repo previously "fixed" it by
halving max_tokens, which treated the symptom.)

Two consequences shape this module:

1. Budgets are per-model, so spreading agents across models multiplies usable
   throughput rather than merely rebalancing it.
2. Pacing has to happen before the request, because the provider's response to
   overspending is a hard failure rather than a queue.

A sliding 60-second window per model is tracked locally and reconciled against
the `x-ratelimit-remaining-tokens` header, so estimation error self-corrects.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Deque, Dict, Mapping, Optional, Tuple

from ..core.logging.logger import app_logger

WINDOW_SECONDS = 60.0
#: Fraction of the advertised budget to actually spend. Token estimates are
#: approximate and the provider's window may not align with ours.
SAFETY_FACTOR = 0.90


def estimate_tokens(text: str) -> int:
    """Rough prompt-token estimate. ~4 characters per token for English."""
    return max(1, len(text) // 4)


class ModelBucket:
    """Sliding-window token budget for a single model."""

    def __init__(self, model: str, tokens_per_minute: int):
        self.model = model
        self.limit = max(1, int(tokens_per_minute * SAFETY_FACTOR))
        self._events: Deque[Tuple[float, int]] = deque()
        self._lock = asyncio.Lock()
        self._reported_remaining: Optional[int] = None
        self._reported_at: float = 0.0

    def _spent(self, now: float) -> int:
        while self._events and now - self._events[0][0] > WINDOW_SECONDS:
            self._events.popleft()
        return sum(tokens for _, tokens in self._events)

    def _wait_for(self, now: float, deficit: int) -> float:
        """Seconds until enough queued tokens age out to cover `deficit`.

        Waiting only for the single oldest entry is the tempting version and it
        is wrong: if that entry is small, the budget is still short afterwards
        and the next iteration sleeps again, turning one necessary pause into
        several full windows. Accumulate expiries until the deficit is covered.
        """
        freed = 0
        for timestamp, tokens in self._events:
            freed += tokens
            if freed >= deficit:
                return max(0.0, WINDOW_SECONDS - (now - timestamp)) + 0.05
        return WINDOW_SECONDS

    async def acquire(self, estimated: int) -> None:
        """Block until `estimated` tokens fit inside the window."""
        async with self._lock:
            while True:
                now = time.monotonic()
                spent = self._spent(now)

                if spent + estimated <= self.limit or not self._events:
                    # Let a single oversized request through rather than
                    # deadlocking on a budget it can never fit into; the
                    # provider will reject it and the retry path handles that.
                    self._events.append((now, estimated))
                    return

                wait = max(0.25, self._wait_for(now, spent + estimated - self.limit))
                app_logger.info(
                    "Pacing for token budget",
                    model=self.model,
                    spent_in_window=spent,
                    requested=estimated,
                    limit=self.limit,
                    waiting_seconds=round(wait, 1),
                )
                await asyncio.sleep(wait)

    def observe(self, headers: Mapping[str, str], actual_tokens: int) -> None:
        """Reconcile the local window with the provider's own accounting."""
        if self._events:
            timestamp, estimated = self._events[-1]
            if actual_tokens > 0:
                self._events[-1] = (timestamp, actual_tokens)

        remaining = headers.get("x-ratelimit-remaining-tokens")
        if remaining is not None:
            try:
                self._reported_remaining = int(float(remaining))
                self._reported_at = time.monotonic()
            except ValueError:
                pass

        limit_header = headers.get("x-ratelimit-limit-tokens")
        if limit_header is not None:
            try:
                advertised = int(float(limit_header))
                scaled = max(1, int(advertised * SAFETY_FACTOR))
                if scaled != self.limit:
                    app_logger.info(
                        "Adjusting token budget from provider headers",
                        model=self.model,
                        advertised=advertised,
                        limit=scaled,
                    )
                    self.limit = scaled
            except ValueError:
                pass

    @property
    def status(self) -> Dict[str, object]:
        return {
            "model": self.model,
            "limit": self.limit,
            "spent_in_window": self._spent(time.monotonic()),
            "provider_remaining": self._reported_remaining,
        }


class RateLimiter:
    """Registry of per-model buckets."""

    def __init__(self, default_tpm: int):
        self.default_tpm = default_tpm
        self._buckets: Dict[str, ModelBucket] = {}

    def bucket(self, model: str) -> ModelBucket:
        if model not in self._buckets:
            self._buckets[model] = ModelBucket(model, self.default_tpm)
        return self._buckets[model]

    @property
    def status(self) -> Dict[str, object]:
        return {model: bucket.status for model, bucket in self._buckets.items()}


_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        from ..core.config.settings import settings

        _limiter = RateLimiter(settings.GROQ_TPM_LIMIT)
    return _limiter
