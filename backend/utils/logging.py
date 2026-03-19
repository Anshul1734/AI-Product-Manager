import logging
import time
import random
import traceback
from typing import Any, Dict, Optional
from functools import wraps

# Configure structured logging
def setup_logger(name: str = "ai_product_manager") -> logging.Logger:
    """Set up a structured logger with consistent formatting"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Create console handler
        console_handler = logging.StreamHandler()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    
    return logger

# Global logger instance
logger = setup_logger()

class PipelineLogger:
    """Enhanced logging for AI Product Manager pipeline"""
    
    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or f"req_{int(time.time())}_{random.randint(1000, 9999)}"
    
    def log_start(self, idea: str, thread_id: Optional[str] = None, use_legacy: bool = False):
        """Log the start of a pipeline execution"""
        logger.info(f"[{self.request_id}] === NEW REQUEST RECEIVED ===")
        logger.info(f"[{self.request_id}] Request Details:")
        logger.info(f"[{self.request_id}]   - Idea: {idea[:100]}{'...' if len(idea) > 100 else ''}")
        logger.info(f"[{self.request_id}]   - Thread ID: {thread_id}")
        logger.info(f"[{self.request_id}]   - Use Legacy: {use_legacy}")
        logger.info(f"[{self.request_id}] Starting pipeline execution...")
    
    def log_agent_start(self, agent_name: str):
        """Log the start of an agent execution"""
        logger.info(f"[{self.request_id}] 🤖 STEP: {agent_name.upper()} AGENT")
    
    def log_agent_complete(self, agent_name: str, execution_time: float, result_summary: Dict[str, Any]):
        """Log the completion of an agent execution"""
        logger.info(f"[{self.request_id}]   ✅ {agent_name.title()} completed in {execution_time:.2f}s")
        
        # Log specific details based on agent
        if agent_name == "planner":
            logger.info(f"[{self.request_id}]   📋 Generated: {result_summary.get('product_name', 'N/A')}")
            logger.info(f"[{self.request_id}]   🎯 Problem: {result_summary.get('problem_statement', 'N/A')[:80]}...")
        elif agent_name == "analyst":
            logger.info(f"[{self.request_id}]   👥 Target Users: {len(result_summary.get('target_users', []))} groups")
            logger.info(f"[{self.request_id}]   📝 User Stories: {len(result_summary.get('user_stories', []))} stories")
            logger.info(f"[{self.request_id}]   📊 Success Metrics: {len(result_summary.get('success_metrics', []))} metrics")
        elif agent_name == "architect":
            logger.info(f"[{self.request_id}]   🏗️  Architecture: {result_summary.get('system_design', 'N/A')}")
            tech_stack = result_summary.get('tech_stack', {})
            logger.info(f"[{self.request_id}]   🔧 Tech Stack: {', '.join(tech_stack.keys()) if tech_stack else 'N/A'}")
            logger.info(f"[{self.request_id}]   📦 Components: {len(result_summary.get('architecture_components', []))} services")
        elif agent_name == "ticket_generator":
            logger.info(f"[{self.request_id}]   📋 Epics: {len(result_summary.get('epics', []))}")
            total_stories = sum(len(epic.get('stories', [])) for epic in result_summary.get('epics', []))
            logger.info(f"[{self.request_id}]   📝 Stories: {total_stories}")
            total_tasks = sum(len(story.get('tasks', [])) for epic in result_summary.get('epics', []) for story in epic.get('stories', []))
            logger.info(f"[{self.request_id}]   ✅ Tasks: {total_tasks}")
    
    def log_pipeline_complete(self, total_time: float, agent_times: Dict[str, float], thread_id: str):
        """Log the completion of the entire pipeline"""
        logger.info(f"[{self.request_id}] ✅ PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"[{self.request_id}] 📊 EXECUTION SUMMARY:")
        logger.info(f"[{self.request_id}]   - Total Time: {total_time:.2f}s")
        for agent, time_taken in agent_times.items():
            logger.info(f"[{self.request_id}]   - {agent.title()}: {time_taken:.2f}s")
        logger.info(f"[{self.request_id}]   - Thread ID: {thread_id}")
        logger.info(f"[{self.request_id}] 🎉 RESPONSE READY FOR CLIENT")
    
    def log_pipeline_error(self, error: Exception, thread_id: Optional[str] = None):
        """Log pipeline errors with detailed information"""
        logger.error(f"[{self.request_id}] ❌ PIPELINE FAILED")
        logger.error(f"[{self.request_id}]   Error Type: {type(error).__name__}")
        logger.error(f"[{self.request_id}]   Error Message: {str(error)}")
        logger.error(f"[{self.request_id}]   Error Details: {repr(error)}")
        logger.error(f"[{self.request_id}]   Stack Trace: {traceback.format_exc()}")
        logger.error(f"[{self.request_id}] 🚨 ERROR RESPONSE SENT TO CLIENT")
    
    def log_validation_start(self, idea: str, thread_id: Optional[str] = None):
        """Log validation request start"""
        logger.info(f"[{self.request_id}] 🔍 VALIDATION REQUEST")
        logger.info(f"[{self.request_id}]   - Idea: {idea[:100]}{'...' if len(idea) > 100 else ''}")
        logger.info(f"[{self.request_id}]   - Thread ID: {thread_id}")
    
    def log_validation_complete(self, is_valid: bool, issues_count: int, suggestions_count: int):
        """Log validation completion"""
        logger.info(f"[{self.request_id}] ✅ VALIDATION COMPLETED")
        logger.info(f"[{self.request_id}]   - Valid: {is_valid}")
        logger.info(f"[{self.request_id}]   - Issues Found: {issues_count}")
        logger.info(f"[{self.request_id}]   - Suggestions: {suggestions_count}")
    
    def log_validation_error(self, error: Exception):
        """Log validation errors"""
        logger.error(f"[{self.request_id}] ❌ VALIDATION FAILED")
        logger.error(f"[{self.request_id}]   Error: {str(error)}")
    
    def log_health_check(self):
        """Log health check"""
        logger.info(f"[{self.request_id}] 💓 HEALTH CHECK")
        logger.info(f"[{self.request_id}]   - Status: Checking system health")
        logger.info(f"[{self.request_id}]   - Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def log_health_complete(self, status: str):
        """Log health check completion"""
        logger.info(f"[{self.request_id}] ✅ HEALTH CHECK COMPLETED")
        logger.info(f"[{self.request_id}]   - Response: {status}")

def log_pipeline_step(agent_name: str):
    """Decorator for logging pipeline steps"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request_id from kwargs or create new one
            request_id = kwargs.get('request_id')
            pipeline_logger = PipelineLogger(request_id)
            
            # Log agent start
            pipeline_logger.log_agent_start(agent_name)
            
            # Execute the function
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log successful completion
                pipeline_logger.log_agent_complete(agent_name, execution_time, result)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                pipeline_logger.log_agent_complete(agent_name, execution_time, {"error": str(e)})
                raise
                
        return wrapper
    return decorator

def log_api_call(endpoint_name: str):
    """Decorator for logging API calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request_id = f"api_{int(time.time())}_{random.randint(1000, 9999)}"
            pipeline_logger = PipelineLogger(request_id)
            
            logger.info(f"[{request_id}] 🌐 API CALL: {endpoint_name.upper()}")
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"[{request_id}] ✅ API CALL COMPLETED")
                logger.info(f"[{request_id}]   - Duration: {execution_time:.2f}s")
                logger.info(f"[{request_id}]   - Status: Success")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"[{request_id}] ❌ API CALL FAILED")
                logger.error(f"[{request_id}]   - Duration: {execution_time:.2f}s")
                logger.error(f"[{request_id}]   - Error: {str(e)}")
                raise
                
        return wrapper
    return decorator
