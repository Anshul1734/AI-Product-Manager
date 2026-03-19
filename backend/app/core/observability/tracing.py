"""
Distributed tracing system for request tracking.
"""
import uuid
import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager
import json

from ..config.settings import settings
from ..logging.logger import app_logger


@dataclass
class Span:
    """Trace span representing an operation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    error: Optional[str] = None


@dataclass
class Trace:
    """Complete trace with multiple spans."""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    tags: Dict[str, Any] = field(default_factory=dict)


class TracingService:
    """Advanced distributed tracing service."""
    
    def __init__(self, max_traces: int = 1000):
        self.max_traces = max_traces
        self.traces: Dict[str, Trace] = {}
        self.active_spans: Dict[str, Span] = {}
        self.logger = app_logger
        self._lock = asyncio.Lock()
        self.enabled = settings.OBSERVABILITY_ENABLED
    
    def generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        return str(uuid.uuid4())
    
    def generate_span_id(self) -> str:
        """Generate a unique span ID."""
        return str(uuid.uuid4())
    
    async def start_span(
        self, 
        operation_name: str, 
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Start a new span."""
        if not self.enabled:
            # Return dummy span for disabled tracing
            return Span(
                trace_id="disabled",
                span_id="disabled",
                parent_span_id=None,
                operation_name=operation_name,
                start_time=datetime.utcnow()
            )
        
        trace_id = trace_id or self.generate_trace_id()
        span_id = self.generate_span_id()
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.utcnow(),
            tags=tags or {}
        )
        
        async with self._lock:
            # Store active span
            self.active_spans[span_id] = span
            
            # Ensure trace exists
            if trace_id not in self.traces:
                self.traces[trace_id] = Trace(trace_id=trace_id)
            
            # Add span to trace
            self.traces[trace_id].spans.append(span)
            
            # Cleanup old traces
            if len(self.traces) > self.max_traces:
                await self._cleanup_old_traces()
        
        self.logger.debug(
            f"Started span: {operation_name}",
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        return span
    
    async def finish_span(
        self, 
        span_id: str, 
        status: str = "ok", 
        error: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ):
        """Finish a span."""
        if not self.enabled:
            return
        
        async with self._lock:
            span = self.active_spans.pop(span_id, None)
            if not span:
                self.logger.warning(f"Attempted to finish non-existent span: {span_id}")
                return
            
            span.end_time = datetime.utcnow()
            span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
            span.status = status
            span.error = error
            
            if tags:
                span.tags.update(tags)
            
            # Update trace end time
            trace = self.traces.get(span.trace_id)
            if trace:
                trace.end_time = span.end_time
            
            self.logger.debug(
                f"Finished span: {span.operation_name}",
                trace_id=span.trace_id,
                span_id=span_id,
                duration_ms=span.duration_ms,
                status=status
            )
    
    async def add_span_log(self, span_id: str, level: str, message: str, fields: Optional[Dict[str, Any]] = None):
        """Add a log entry to a span."""
        if not self.enabled:
            return
        
        async with self._lock:
            span = self.active_spans.get(span_id)
            if not span:
                # Check if it's a finished span
                for trace in self.traces.values():
                    for s in trace.spans:
                        if s.span_id == span_id:
                            span = s
                            break
            
            if span:
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": level,
                    "message": message,
                    "fields": fields or {}
                }
                span.logs.append(log_entry)
    
    @asynccontextmanager
    async def trace_span(
        self, 
        operation_name: str, 
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ):
        """Context manager for tracing operations."""
        span = await self.start_span(operation_name, trace_id, parent_span_id, tags)
        
        try:
            yield span
            await self.finish_span(span.span_id, "ok")
        except Exception as e:
            await self.finish_span(span.span_id, "error", str(e))
            raise
    
    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a complete trace."""
        async with self._lock:
            return self.traces.get(trace_id)
    
    async def get_span(self, span_id: str) -> Optional[Span]:
        """Get a specific span."""
        async with self._lock:
            # Check active spans first
            if span_id in self.active_spans:
                return self.active_spans[span_id]
            
            # Check finished spans
            for trace in self.traces.values():
                for span in trace.spans:
                    if span.span_id == span_id:
                        return span
        
        return None
    
    async def get_trace_summaries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trace summaries."""
        async with self._lock:
            summaries = []
            for trace_id, trace in list(self.traces.items())[-limit:]:
                total_duration = 0
                span_count = len(trace.spans)
                error_count = sum(1 for span in trace.spans if span.status == "error")
                
                for span in trace.spans:
                    if span.duration_ms:
                        total_duration += span.duration_ms
                
                summaries.append({
                    "trace_id": trace_id,
                    "span_count": span_count,
                    "error_count": error_count,
                    "total_duration_ms": total_duration,
                    "start_time": trace.start_time.isoformat(),
                    "end_time": trace.end_time.isoformat() if trace.end_time else None,
                    "tags": trace.tags
                })
            
            return sorted(summaries, key=lambda x: x["start_time"], reverse=True)
    
    async def search_traces(self, query: Dict[str, Any], limit: int = 50) -> List[Trace]:
        """Search traces by criteria."""
        async with self._lock:
            results = []
            
            for trace in list(self.traces.values()):
                matches = True
                
                # Search by operation name
                if "operation_name" in query:
                    operation_name = query["operation_name"]
                    if not any(span.operation_name == operation_name for span in trace.spans):
                        matches = False
                
                # Search by status
                if "status" in query:
                    status = query["status"]
                    if not any(span.status == status for span in trace.spans):
                        matches = False
                
                # Search by tags
                if "tags" in query:
                    tags = query["tags"]
                    for key, value in tags.items():
                        if trace.tags.get(key) != value:
                            matches = False
                            break
                
                if matches:
                    results.append(trace)
                    if len(results) >= limit:
                        break
            
            return results
    
    async def _cleanup_old_traces(self):
        """Clean up old traces."""
        if len(self.traces) <= self.max_traces:
            return
        
        # Sort traces by start time and keep the most recent
        sorted_traces = sorted(
            self.traces.items(),
            key=lambda x: x[1].start_time,
            reverse=True
        )
        
        # Keep only the most recent traces
        self.traces = dict(sorted_traces[:self.max_traces])
        
        self.logger.debug(f"Cleaned up old traces, kept {len(self.traces)} traces")
    
    async def get_tracing_stats(self) -> Dict[str, Any]:
        """Get tracing statistics."""
        async with self._lock:
            total_traces = len(self.traces)
            active_spans = len(self.active_spans)
            
            total_spans = sum(len(trace.spans) for trace in self.traces.values())
            error_spans = sum(
                1 for trace in self.traces.values()
                for span in trace.spans
                if span.status == "error"
            )
            
            avg_duration = 0
            all_durations = [
                span.duration_ms for trace in self.traces.values()
                for span in trace.spans
                if span.duration_ms is not None
            ]
            
            if all_durations:
                avg_duration = sum(all_durations) / len(all_durations)
            
            return {
                "enabled": self.enabled,
                "total_traces": total_traces,
                "active_spans": active_spans,
                "total_spans": total_spans,
                "error_spans": error_spans,
                "error_rate": error_spans / total_spans if total_spans > 0 else 0,
                "avg_duration_ms": avg_duration,
                "max_traces": self.max_traces
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get tracing system health status."""
        return {
            "status": "healthy",
            "enabled": self.enabled,
            "trace_count": len(self.traces),
            "active_span_count": len(self.active_spans),
            "max_traces": self.max_traces
        }


def create_tracing_service() -> TracingService:
    """Create and configure tracing service."""
    return TracingService(max_traces=1000)
