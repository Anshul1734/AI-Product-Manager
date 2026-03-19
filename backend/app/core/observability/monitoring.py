"""
Comprehensive monitoring service for system health and performance.
"""
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

from ..config.settings import settings
from ..logging.logger import app_logger
from .metrics import MetricsCollector
from .tracing import TracingService


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_type: str
    timeout: float
    threshold: Optional[float] = None
    description: str = ""


@dataclass
class HealthResult:
    """Health check result."""
    name: str
    status: str  # healthy, warning, critical
    message: str
    duration_ms: float
    timestamp: datetime
    details: Dict[str, Any] = None


class MonitoringService:
    """Advanced monitoring service for system health and performance."""
    
    def __init__(self, metrics_collector: MetricsCollector, tracing_service: TracingService):
        self.metrics = metrics_collector
        self.tracing = tracing_service
        self.logger = app_logger
        self.health_checks: List[HealthCheck] = []
        self.alerts: List[Dict[str, Any]] = []
        self._setup_default_health_checks()
    
    def _setup_default_health_checks(self):
        """Setup default health checks."""
        self.health_checks = [
            HealthCheck(
                name="memory_usage",
                check_type="system",
                timeout=5.0,
                threshold=80.0,
                description="System memory usage percentage"
            ),
            HealthCheck(
                name="agent_response_time",
                check_type="system",
                timeout=10.0,
                threshold=5000.0,
                description="Average agent response time in milliseconds"
            ),
            HealthCheck(
                name="error_rate",
                check_type="system",
                timeout=5.0,
                threshold=0.1,
                description="System error rate percentage"
            ),
            HealthCheck(
                name="agent_availability",
                check_type="system",
                timeout=5.0,
                threshold=0.95,
                description="Agent availability percentage"
            )
        ]
    
    async def run_health_check(self, health_check: HealthCheck) -> HealthResult:
        """Run a single health check."""
        start_time = time.time()
        
        try:
            if health_check.name == "memory_usage":
                result = await self._check_memory_usage(health_check)
            elif health_check.name == "agent_response_time":
                result = await self._check_agent_response_time(health_check)
            elif health_check.name == "error_rate":
                result = await self._check_error_rate(health_check)
            elif health_check.name == "agent_availability":
                result = await self._check_agent_availability(health_check)
            else:
                result = HealthResult(
                    name=health_check.name,
                    status="warning",
                    message=f"Unknown health check: {health_check.name}",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.utcnow()
                )
            
            return result
            
        except Exception as e:
            return HealthResult(
                name=health_check.name,
                status="critical",
                message=f"Health check failed: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                details={"error": str(e)}
            )
    
    async def _check_memory_usage(self, health_check: HealthCheck) -> HealthResult:
        """Check system memory usage."""
        import psutil
        
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        status = "healthy"
        if usage_percent > health_check.threshold:
            status = "critical"
        elif usage_percent > health_check.threshold * 0.8:
            status = "warning"
        
        return HealthResult(
            name=health_check.name,
            status=status,
            message=f"Memory usage: {usage_percent:.1f}%",
            duration_ms=0,
            timestamp=datetime.utcnow(),
            details={
                "usage_percent": usage_percent,
                "available_gb": memory.available / (1024**3),
                "total_gb": memory.total / (1024**3),
                "threshold": health_check.threshold
            }
        )
    
    async def _check_agent_response_time(self, health_check: HealthCheck) -> HealthResult:
        """Check agent response time."""
        # Get average response time from metrics
        summary = await self.metrics.get_summary("agent_duration")
        
        if not summary:
            return HealthResult(
                name=health_check.name,
                status="warning",
                message="No agent response time data available",
                duration_ms=0,
                timestamp=datetime.utcnow()
            )
        
        avg_duration = summary.avg_value
        status = "healthy"
        
        if avg_duration > health_check.threshold:
            status = "critical"
        elif avg_duration > health_check.threshold * 0.7:
            status = "warning"
        
        return HealthResult(
            name=health_check.name,
            status=status,
            message=f"Average response time: {avg_duration:.1f}ms",
            duration_ms=0,
            timestamp=datetime.utcnow(),
            details={
                "avg_duration_ms": avg_duration,
                "min_duration_ms": summary.min_value,
                "max_duration_ms": summary.max_value,
                "count": summary.count,
                "threshold": health_check.threshold
            }
        )
    
    async def _check_error_rate(self, health_check: HealthCheck) -> HealthResult:
        """Check system error rate."""
        # Calculate error rate from metrics
        total_calls = await self.metrics.get_counter("agent_calls")
        error_calls = await self.metrics.get_counter("agent_errors")
        
        if total_calls == 0:
            return HealthResult(
                name=health_check.name,
                status="healthy",
                message="No agent calls recorded",
                duration_ms=0,
                timestamp=datetime.utcnow(),
                details={"total_calls": 0, "error_calls": 0}
            )
        
        error_rate = error_calls / total_calls
        status = "healthy"
        
        if error_rate > health_check.threshold:
            status = "critical"
        elif error_rate > health_check.threshold * 0.5:
            status = "warning"
        
        return HealthResult(
            name=health_check.name,
            status=status,
            message=f"Error rate: {(error_rate * 100):.1f}%",
            duration_ms=0,
            timestamp=datetime.utcnow(),
            details={
                "error_rate": error_rate,
                "total_calls": total_calls,
                "error_calls": error_calls,
                "threshold": health_check.threshold
            }
        )
    
    async def _check_agent_availability(self, health_check: HealthCheck) -> HealthResult:
        """Check agent availability."""
        # Get agent success rate
        success_calls = await self.metrics.get_counter("agent_success")
        total_calls = await self.metrics.get_counter("agent_calls")
        
        if total_calls == 0:
            return HealthResult(
                name=health_check.name,
                status="warning",
                message="No agent calls recorded",
                duration_ms=0,
                timestamp=datetime.utcnow()
            )
        
        availability = success_calls / total_calls
        status = "healthy"
        
        if availability < health_check.threshold:
            status = "critical"
        elif availability < health_check.threshold * 0.9:
            status = "warning"
        
        return HealthResult(
            name=health_check.name,
            status=status,
            message=f"Agent availability: {(availability * 100):.1f}%",
            duration_ms=0,
            timestamp=datetime.utcnow(),
            details={
                "availability": availability,
                "success_calls": success_calls,
                "total_calls": total_calls,
                "threshold": health_check.threshold
            }
        )
    
    async def run_all_health_checks(self) -> List[HealthResult]:
        """Run all health checks."""
        results = []
        
        for health_check in self.health_checks:
            result = await self.run_health_check(health_check)
            results.append(result)
            
            # Record metrics
            await self.metrics.set_gauge(
                f"health_check_{result.name}",
                1.0 if result.status == "healthy" else 0.0,
                {"status": result.status}
            )
        
        return results
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health."""
        health_results = await self.run_all_health_checks()
        
        # Determine overall status
        critical_count = sum(1 for r in health_results if r.status == "critical")
        warning_count = sum(1 for r in health_results if r.status == "warning")
        
        if critical_count > 0:
            overall_status = "critical"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [
                {
                    "name": r.name,
                    "status": r.status,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "details": r.details
                }
                for r in health_results
            ],
            "summary": {
                "total_checks": len(health_results),
                "healthy": sum(1 for r in health_results if r.status == "healthy"),
                "warnings": warning_count,
                "critical": critical_count
            }
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        # Get metrics summaries
        summaries = await self.metrics.get_all_summaries()
        
        # Get tracing stats
        tracing_stats = await self.tracing.get_tracing_stats()
        
        # Get recent performance data
        recent_metrics = {}
        for name in ["agent_duration", "agent_calls", "agent_success", "agent_errors"]:
            summary = await self.metrics.get_summary(name)
            if summary:
                recent_metrics[name] = {
                    "count": summary.count,
                    "avg": summary.avg_value,
                    "min": summary.min_value,
                    "max": summary.max_value,
                    "last_updated": summary.last_updated.isoformat()
                }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": recent_metrics,
            "tracing": tracing_stats,
            "health": await self.get_system_health()
        }
    
    async def create_alert(
        self, 
        alert_type: str, 
        severity: str, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        """Create an alert."""
        alert = {
            "id": str(int(time.time() * 1000)),
            "type": alert_type,
            "severity": severity,  # info, warning, critical
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        
        # Log alert
        self.logger.warning(
            f"Alert created: {alert_type}",
            severity=severity,
            message=message
        )
        
        # Record alert metric
        await self.metrics.increment_counter(f"alert_{alert_type}", 1, {"severity": severity})
    
    async def get_alerts(
        self, 
        severity: Optional[str] = None, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        
        return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    async def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health": await self.get_system_health(),
            "performance": await self.get_performance_metrics(),
            "alerts": await self.get_alerts(limit=10),
            "metrics": {
                "health": await self.metrics.get_health_status(),
                "tracing": self.tracing.get_health_status()
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get monitoring system health status."""
        return {
            "status": "healthy",
            "health_checks_count": len(self.health_checks),
            "alerts_count": len(self.alerts),
            "metrics_enabled": settings.METRICS_ENABLED,
            "tracing_enabled": settings.OBSERVABILITY_ENABLED
        }


def create_monitoring_service(metrics_collector: MetricsCollector, tracing_service: TracingService) -> MonitoringService:
    """Create and configure monitoring service."""
    return MonitoringService(metrics_collector, tracing_service)
