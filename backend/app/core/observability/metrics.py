"""
Metrics collection system for comprehensive monitoring.
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

from ..config.settings import settings
from ..logging.logger import app_logger


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Metric summary statistics."""
    name: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    sum_value: float
    last_updated: datetime


class MetricsCollector:
    """Advanced metrics collection system."""
    
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.summaries: Dict[str, MetricSummary] = {}
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.logger = app_logger
        self._lock = asyncio.Lock()
    
    async def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        async with self._lock:
            timestamp = datetime.utcnow()
            self.counters[name] += value
            
            # Store as metric point
            metric_point = MetricPoint(
                timestamp=timestamp,
                value=float(value),
                tags=tags or {},
                metadata={"type": "counter"}
            )
            self.metrics[name].append(metric_point)
            
            # Update summary
            await self._update_summary(name, metric_point)
    
    async def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        async with self._lock:
            timestamp = datetime.utcnow()
            self.gauges[name] = value
            
            # Store as metric point
            metric_point = MetricPoint(
                timestamp=timestamp,
                value=value,
                tags=tags or {},
                metadata={"type": "gauge"}
            )
            self.metrics[name].append(metric_point)
            
            # Update summary
            await self._update_summary(name, metric_point)
    
    async def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram metric."""
        async with self._lock:
            timestamp = datetime.utcnow()
            self.histograms[name].append(value)
            
            # Keep only recent values
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            
            # Store as metric point
            metric_point = MetricPoint(
                timestamp=timestamp,
                value=value,
                tags=tags or {},
                metadata={"type": "histogram"}
            )
            self.metrics[name].append(metric_point)
            
            # Update summary
            await self._update_summary(name, metric_point)
    
    async def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record timing metric."""
        await self.record_histogram(f"{name}_duration", duration, tags)
        await self.increment_counter(f"{name}_calls", 1, tags)
    
    async def get_metric(self, name: str, since: Optional[datetime] = None) -> List[MetricPoint]:
        """Get metric points."""
        async with self._lock:
            points = list(self.metrics[name])
            
            if since:
                points = [p for p in points if p.timestamp >= since]
            
            return points
    
    async def get_summary(self, name: str) -> Optional[MetricSummary]:
        """Get metric summary."""
        async with self._lock:
            return self.summaries.get(name)
    
    async def get_all_summaries(self) -> Dict[str, MetricSummary]:
        """Get all metric summaries."""
        async with self._lock:
            return dict(self.summaries)
    
    async def get_counter(self, name: str) -> int:
        """Get counter value."""
        async with self._lock:
            return self.counters.get(name, 0)
    
    async def get_gauge(self, name: str) -> Optional[float]:
        """Get gauge value."""
        async with self._lock:
            return self.gauges.get(name)
    
    async def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        async with self._lock:
            values = self.histograms[name]
            if not values:
                return {}
            
            values.sort()
            count = len(values)
            
            return {
                "count": count,
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / count,
                "p50": values[int(count * 0.5)],
                "p95": values[int(count * 0.95)],
                "p99": values[int(count * 0.99)]
            }
    
    async def reset_metric(self, name: str):
        """Reset a specific metric."""
        async with self._lock:
            self.metrics[name].clear()
            self.counters[name] = 0
            self.gauges.pop(name, None)
            self.histograms[name].clear()
            self.summaries.pop(name, None)
    
    async def reset_all_metrics(self):
        """Reset all metrics."""
        async with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.summaries.clear()
    
    async def _update_summary(self, name: str, point: MetricPoint):
        """Update metric summary."""
        points = self.metrics[name]
        if not points:
            return
        
        values = [p.value for p in points]
        
        self.summaries[name] = MetricSummary(
            name=name,
            count=len(points),
            min_value=min(values),
            max_value=max(values),
            avg_value=sum(values) / len(values),
            sum_value=sum(values),
            last_updated=datetime.utcnow()
        )
    
    async def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format."""
        async with self._lock:
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "summaries": {k: {
                    "name": v.name,
                    "count": v.count,
                    "min": v.min_value,
                    "max": v.max_value,
                    "avg": v.avg_value,
                    "last_updated": v.last_updated.isoformat()
                } for k, v in self.summaries.items()},
                "histograms": {k: await self.get_histogram_stats(k) for k in self.histograms.keys()}
            }
            
            if format.lower() == "json":
                return json.dumps(data, indent=2, default=str)
            else:
                return str(data)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get metrics system health status."""
        return {
            "status": "healthy",
            "metrics_count": len(self.metrics),
            "counters_count": len(self.counters),
            "gauges_count": len(self.gauges),
            "histograms_count": len(self.histograms),
            "max_points": self.max_points,
            "total_points": sum(len(points) for points in self.metrics.values())
        }


def create_metrics_collector() -> MetricsCollector:
    """Create and configure metrics collector."""
    return MetricsCollector(max_points=10000)
