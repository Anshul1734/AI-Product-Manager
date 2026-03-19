"""
Workflow router for the AI Product Manager API.
"""
import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..core import app_logger, settings, request_context, RateLimitError
from ..schemas import ProductIdeaRequest, WorkflowResponse, ValidationRequest, ValidationResponse
from ..services.product_service import generate_product_plan


router = APIRouter()


@router.post("/generate", response_model=WorkflowResponse)
async def generate_product_plan(request: ProductIdeaRequest) -> WorkflowResponse:
    """Generate a complete product plan from an idea using Groq API."""
    with request_context(app_logger, "POST", "/generate", idea=request.idea[:100]):
        try:
            start_time = time.time()
            
            # Generate product plan with Groq - single call, fast response
            result = generate_product_plan(request.idea)
            
            execution_time = time.time() - start_time
            
            # Log successful execution
            app_logger.info(
                "Product plan generated successfully with Groq",
                idea=request.idea[:200],
                thread_id=request.thread_id,
                execution_time=execution_time
            )
            
            return WorkflowResponse(
                success=True,
                message="Product plan generated successfully using Groq",
                data={
                    "result": result,
                    "generated_at": time.time(),
                    "model": "Groq API",
                    "execution_time": execution_time
                },
                execution_time=execution_time,
                thread_id=request.thread_id,
                request_id=getattr(request.state, "request_id", None)
            )
            
        except Exception as e:
            app_logger.error(
                "Product plan generation failed",
                idea=request.idea[:200] if request.idea else "N/A",
                thread_id=request.thread_id,
                error=str(e)
            )
            
            return WorkflowResponse(
                success=False,
                message=f"Failed to generate product plan: {str(e)}",
                request_id=getattr(request.state, "request_id", None)
            )


@router.post("/validate", response_model=ValidationResponse)
async def validate_product_idea(request: ValidationRequest) -> ValidationResponse:
    """Validate a product idea and provide feedback."""
    with request_context(app_logger, "POST", "/validate", idea=request.idea[:100]):
        try:
            # Basic validation
            issues = []
            suggestions = []
            
            # Check length
            if len(request.idea.strip()) < 10:
                issues.append("Product idea is too short (minimum 10 characters)")
                suggestions.append("Provide more detail about your product idea")
            
            # Check for common issues
            idea_lower = request.idea.lower()
            if not any(word in idea_lower for word in ["problem", "solve", "help", "need", "want"]):
                issues.append("Product idea doesn't clearly state the problem it solves")
                suggestions.append("Include the problem your product solves")
            
            if not any(word in idea_lower for word in ["user", "customer", "people", "market"]):
                issues.append("Product idea doesn't mention target users")
                suggestions.append("Specify who your target users are")
            
            if len(request.idea.strip()) > 1000:
                issues.append("Product idea is quite long")
                suggestions.append("Consider making it more concise while keeping key details")
            
            # Calculate confidence score
            confidence_score = max(0.0, 1.0 - (len(issues) * 0.2))
            
            return ValidationResponse(
                success=True,
                valid=len(issues) == 0,
                issues=issues,
                suggestions=suggestions,
                confidence_score=confidence_score,
                request_id=None
            )
            
        except Exception as e:
            app_logger.error(
                "Product idea validation failed",
                idea=request.idea[:200] if request.idea else "N/A",
                thread_id=request.thread_id,
                error=str(e)
            )
            
            return ValidationResponse(
                success=False,
                valid=False,
                issues=[f"Validation error: {str(e)}"],
                suggestions=["Please try again with a different input"],
                request_id=None
            )


@router.get("/status")
async def get_workflow_status() -> Dict[str, Any]:
    """Get workflow service status."""
    try:
        status = workflow_service.get_workflow_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        app_logger.error(f"Workflow status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get workflow status")
