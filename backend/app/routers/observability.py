"""
Observability router for the AI Product Manager API.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..core import app_logger, create_metrics_collector, create_tracing_service, create_monitoring_service


router = APIRouter()

# Global instances (in production, these would be dependency injected)
metrics_collector = create_metrics_collector()
tracing_service = create_tracing_service()
monitoring_service = create_monitoring_service(metrics_collector, tracing_service)


class MetricRequest(BaseModel):
    """Request model for adding metrics."""
    name: str
    value: float
    metric_type: str  # counter, gauge, histogram
    tags: Optional[Dict[str, str]] = None


class AlertRequest(BaseModel):
    """Request model for creating alerts."""
    alert_type: str
    severity: str  # info, warning, critical
    message: str
    details: Optional[Dict[str, Any]] = None


@router.post("/observability/metrics/counter")
async def increment_counter(request: MetricRequest):
    """Increment a counter metric."""
    try:
        await metrics_collector.increment_counter(
            name=request.name,
            value=int(request.value),
            tags=request.tags
        )
        
        return {
            "success": True,
            "message": f"Counter {request.name} incremented by {int(request.value)}"
        }
        
    except Exception as e:
        app_logger.error("Failed to increment counter", metric_name=request.name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to increment counter")


@router.post("/observability/metrics/gauge")
async def set_gauge(request: MetricRequest):
    """Set a gauge metric."""
    try:
        await metrics_collector.set_gauge(
            name=request.name,
            value=request.value,
            tags=request.tags
        )
        
        return {
            "success": True,
            "message": f"Gauge {request.name} set to {request.value}"
        }
        
    except Exception as e:
        app_logger.error("Failed to set gauge", metric_name=request.name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to set gauge")


@router.post("/observability/metrics/histogram")
async def record_histogram(request: MetricRequest):
    """Record a histogram metric."""
    try:
        await metrics_collector.record_histogram(
            name=request.name,
            value=request.value,
            tags=request.tags
        )
        
        return {
            "success": True,
            "message": f"Histogram {request.name} recorded value {request.value}"
        }
        
    except Exception as e:
        app_logger.error("Failed to record histogram", metric_name=request.name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to record histogram")


@router.get("/observability/metrics")
async def get_metrics(
    name: Optional[str] = Query(None),
    format: str = Query("json")
):
    """Get metrics data."""
    try:
        if name:
            # Get specific metric
            summary = await metrics_collector.get_summary(name)
            if not summary:
                raise HTTPException(status_code=404, detail=f"Metric {name} not found")
            
            data = {"summary": summary}
        else:
            # Get all metrics
            data = {
                "summaries": await metrics_collector.get_all_summaries(),
                "counters": dict(metrics_collector.counters),
                "gauges": dict(metrics_collector.gauges)
            }
        
        if format == "json":
            return {
                "success": True,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": True,
                "data": str(data),
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error("Failed to get metrics", metric_name=name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@router.post("/observability/metrics/reset")
async def reset_metrics(name: Optional[str] = Query(None)):
    """Reset metrics."""
    try:
        if name:
            await metrics_collector.reset_metric(name)
            message = f"Metric {name} reset"
        else:
            await metrics_collector.reset_all_metrics()
            message = "All metrics reset"
        
        return {
            "success": True,
            "message": message
        }
        
    except Exception as e:
        app_logger.error("Failed to reset metrics", metric_name=name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reset metrics")


@router.get("/observability/traces")
async def get_traces(
    limit: int = Query(50),
    operation_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get trace summaries."""
    try:
        query = {}
        if operation_name:
            query["operation_name"] = operation_name
        if status:
            query["status"] = status
        
        traces = await tracing_service.get_trace_summaries(limit=limit)
        
        # Filter by query if provided
        if query:
            filtered_traces = []
            for trace in traces:
                matches = True
                
                if "operation_name" in query:
                    if not any(span["operation_name"] == query["operation_name"] for span in trace.get("spans", [])):
                        matches = False
                
                if "status" in query:
                    if not any(span.get("status") == query["status"] for span in trace.get("spans", [])):
                        matches = False
                
                if matches:
                    filtered_traces.append(trace)
            
            traces = filtered_traces
        
        return {
            "success": True,
            "data": traces,
            "query": query,
            "limit": limit
        }
        
    except Exception as e:
        app_logger.error("Failed to get traces", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get traces")


@router.get("/observability/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific trace."""
    try:
        trace = await tracing_service.get_trace(trace_id)
        
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
        
        return {
            "success": True,
            "data": {
                "trace_id": trace.trace_id,
                "spans": [
                    {
                        "span_id": span.span_id,
                        "parent_span_id": span.parent_span_id,
                        "operation_name": span.operation_name,
                        "start_time": span.start_time.isoformat(),
                        "end_time": span.end_time.isoformat() if span.end_time else None,
                        "duration_ms": span.duration_ms,
                        "status": span.status,
                        "tags": span.tags,
                        "logs": span.logs
                    }
                    for span in trace.spans
                ],
                "start_time": trace.start_time.isoformat(),
                "end_time": trace.end_time.isoformat() if trace.end_time else None,
                "tags": trace.tags
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error("Failed to get trace", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get trace")


@router.get("/observability/health")
async def get_system_health():
    """Get comprehensive system health."""
    try:
        health_data = await monitoring_service.get_system_health()
        
        return {
            "success": True,
            "data": health_data
        }
        
    except Exception as e:
        app_logger.error("Failed to get system health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get system health")


@router.get("/observability/performance")
async def get_performance_metrics():
    """Get performance metrics."""
    try:
        performance_data = await monitoring_service.get_performance_metrics()
        
        return {
            "success": True,
            "data": performance_data
        }
        
    except Exception as e:
        app_logger.error("Failed to get performance metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.post("/observability/alerts")
async def create_alert(request: AlertRequest):
    """Create an alert."""
    try:
        await monitoring_service.create_alert(
            alert_type=request.alert_type,
            severity=request.severity,
            message=request.message,
            details=request.details
        )
        
        return {
            "success": True,
            "message": "Alert created successfully"
        }
        
    except Exception as e:
        app_logger.error("Failed to create alert", alert_type=request.alert_type, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create alert")


@router.get("/observability/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """Get recent alerts."""
    try:
        alerts = await monitoring_service.get_alerts(severity=severity, limit=limit)
        
        return {
            "success": True,
            "data": alerts,
            "severity": severity,
            "limit": limit
        }
        
    except Exception as e:
        app_logger.error("Failed to get alerts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.get("/observability/dashboard")
async def get_monitoring_dashboard():
    """Get comprehensive monitoring dashboard data."""
    try:
        dashboard_data = await monitoring_service.get_monitoring_dashboard()
        
        return {
            "success": True,
            "data": dashboard_data
        }
        
    except Exception as e:
        app_logger.error("Failed to get monitoring dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get monitoring dashboard")


@router.get("/observability/stats")
async def get_observability_stats():
    """Get observability system statistics."""
    try:
        stats = {
            "metrics": metrics_collector.get_health_status(),
            "tracing": tracing_service.get_health_status(),
            "monitoring": monitoring_service.get_health_status()
        }
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        app_logger.error("Failed to get observability stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get observability statistics")
