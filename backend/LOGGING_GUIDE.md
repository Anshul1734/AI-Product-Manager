# Backend Logging Guide

This document explains the comprehensive logging system implemented for the AI Product Manager Agent backend.

## 🎯 Purpose

The logging system is designed to:
- Provide clear visibility into the pipeline execution
- Make debugging easier with detailed step-by-step tracking
- Monitor performance metrics for each agent
- Track errors with full context and stack traces
- Enable efficient troubleshooting and optimization

## 📊 Logging Features

### 1. **Request Tracking**
- Unique request IDs for tracing
- Timestamped logs with consistent formatting
- Request details (idea, thread ID, execution mode)

### 2. **Pipeline Visibility**
- Step-by-step agent execution logging
- Individual agent timing and performance metrics
- Output summaries for each agent
- Complete execution timeline

### 3. **Error Handling**
- Detailed error logging with stack traces
- Error context and request information
- Failed pipeline tracking

### 4. **Health Monitoring**
- Health check logging
- System status tracking
- Timestamp monitoring

## 🔧 Log Structure

### Request ID Format
```
req_<timestamp>_<random_number>
val_<timestamp>_<random_number>
health_<timestamp>
```

### Log Levels
- **INFO**: Normal operation, pipeline steps, completions
- **ERROR**: Failures, exceptions, system issues

### Log Categories

#### 🚀 Pipeline Execution
```
[req_1234567890_1234] === NEW REQUEST RECEIVED ===
[req_1234567890_1234] Request Details:
[req_1234567890_1234]   - Idea: AI-powered project management tool...
[req_1234567890_1234]   - Thread ID: test-123
[req_1234567890_1234]   - Use Legacy: false
[req_1234567890_1234] Starting pipeline execution...
```

#### 🤖 Agent Steps
```
[req_1234567890_1234] 🤖 STEP 1: PLANNER AGENT
[req_1234567890_1234]   ✅ Planner completed in 0.50s
[req_1234567890_1234]   📋 Generated: AI-Powered Project Platform
[req_1234567890_1234]   🎯 Problem: Addressing the challenges in...
```

#### 📊 Execution Summary
```
[req_1234567890_1234] ✅ PIPELINE COMPLETED SUCCESSFULLY
[req_1234567890_1234] 📊 EXECUTION SUMMARY:
[req_1234567890_1234]   - Total Time: 2.61s
[req_1234567890_1234]   - Planner: 0.50s
[req_1234567890_1234]   - Analyst: 0.60s
[req_1234567890_1234]   - Architect: 0.69s
[req_1234567890_1234]   - Ticket Generator: 0.81s
[req_1234567890_1234]   - Thread ID: test-123
[req_1234567890_1234] 🎉 RESPONSE READY FOR CLIENT
```

#### ❌ Error Logging
```
[req_1234567890_1234] ❌ PIPELINE FAILED
[req_1234567890_1234]   Error Type: ValueError
[req_1234567890_1234]   Error Message: Invalid input format
[req_1234567890_1234]   Error Details: ValueError('Invalid input format')
[req_1234567890_1234]   Stack Trace: Traceback (most recent call last)...
[req_1234567890_1234] 🚨 ERROR RESPONSE SENT TO CLIENT
```

#### 💓 Health Checks
```
[health_1234567890] 💓 HEALTH CHECK
[health_1234567890]   - Status: Checking system health
[health_1234567890]   - Engine: Mock
[health_1234567890]   - Timestamp: 2026-03-17 16:19:10
[health_1234567890] ✅ HEALTH CHECK COMPLETED
[health_1234567890]   - Response: healthy
```

## 🛠️ Implementation

### PipelineLogger Class

The `PipelineLogger` class provides methods for different logging scenarios:

```python
from utils.logging import PipelineLogger

# Create logger instance
pipeline_logger = PipelineLogger()

# Log pipeline start
pipeline_logger.log_start(idea, thread_id, use_legacy)

# Log agent execution
pipeline_logger.log_agent_start("planner")
# ... agent execution ...
pipeline_logger.log_agent_complete("planner", 0.5, result)

# Log pipeline completion
pipeline_logger.log_pipeline_complete(total_time, agent_times, thread_id)

# Log errors
pipeline_logger.log_pipeline_error(exception, thread_id)
```

### Decorators

For automatic logging of functions:

```python
from utils.logging import log_pipeline_step, log_api_call

# Log pipeline steps
@log_pipeline_step("planner")
async def execute_planner(idea: str) -> dict:
    # Implementation
    pass

# Log API calls
@log_api_call("generate_product_plan")
async def generate_product_plan(request: ProductIdeaRequest):
    # Implementation
    pass
```

## 📈 Performance Monitoring

The logging system tracks:
- **Individual Agent Performance**: Time taken by each agent
- **Pipeline Total Time**: Complete execution duration
- **Request Volume**: Number of requests processed
- **Error Rates**: Failed vs successful requests
- **Resource Usage**: Memory and processing patterns

## 🔍 Debugging Benefits

### 1. **Request Tracing**
- Follow a single request through the entire pipeline
- Identify bottlenecks and performance issues
- Track thread-based conversations

### 2. **Error Diagnosis**
- Full stack traces with context
- Request state at time of error
- Agent-specific error information

### 3. **Performance Analysis**
- Agent execution time breakdown
- Identify slow or failing components
- Optimize pipeline flow

### 4. **System Health**
- Monitor overall system status
- Track uptime and availability
- Detect system issues early

## 🚀 Usage in Production

### Log Levels
- **Development**: INFO and ERROR (full visibility)
- **Staging**: INFO and ERROR (full visibility)
- **Production**: ERROR only (reduce noise)

### Log Aggregation
- Forward logs to centralized logging system
- Use request IDs for distributed tracing
- Set up alerts for error patterns

### Performance Impact
- Minimal overhead (< 5ms per request)
- Asynchronous logging where possible
- Configurable verbosity levels

## 📝 Best Practices

1. **Consistent Request IDs**: Always use the same request ID throughout a pipeline
2. **Structured Messages**: Use consistent formatting and emojis for readability
3. **Error Context**: Include full context when logging errors
4. **Performance Metrics**: Log timing information for performance analysis
5. **Security**: Never log sensitive information (API keys, passwords)

## 🔧 Configuration

### Environment Variables
```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Log format
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# Enable/disable detailed logging
DETAILED_LOGGING=true
```

### Custom Logger Setup
```python
from utils.logging import setup_logger

# Create custom logger
custom_logger = setup_logger("my_component")
```

## 📊 Example Log Output

See the sections above for complete examples of log output for different scenarios. The logging system provides comprehensive visibility into the AI Product Manager Agent pipeline execution.
