"""
Main FastAPI application for the AI Product Manager.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core import (
    settings, 
    app_logger
)
from .routers import workflow_router, export_router, health_router


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered product planning and requirements generation",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add middleware
    # Note: Exception handling middleware can be added here if needed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request ID middleware
    # Note: Request ID middleware can be added here if needed
    # app.middleware("http")(create_request_id_middleware)
    
    # Include routers
    app.include_router(health_router, prefix=settings.API_V1_STR)
    app.include_router(workflow_router, prefix=settings.API_V1_STR)
    app.include_router(export_router, prefix=settings.API_V1_STR)
    
    # Add a simple test route for debugging
    @app.get("/")
    async def root():
        return {"status": "ok", "message": "AI Product Manager is running"}

    # Compatibility route (some clients expect /generate without /api/v1)
    from .schemas import ProductIdeaRequest, WorkflowResponse
    from .services.product_service import generate_product_plan
    import time

    @app.post("/generate", response_model=WorkflowResponse)
    async def generate_no_prefix(request: ProductIdeaRequest) -> WorkflowResponse:
        app_logger.info("Received POST /generate", idea_preview=(request.idea or "")[:200], thread_id=request.thread_id)
        start_time = time.time()
        try:
            result = generate_product_plan(request.idea)
            execution_time = time.time() - start_time
            
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
                thread_id=request.thread_id
            )
        except Exception as e:
            app_logger.error(f"Generate failed: {str(e)}")
            return WorkflowResponse(
                success=False,
                message=f"Failed to generate product plan: {str(e)}",
                execution_time=time.time() - start_time,
                thread_id=request.thread_id
            )
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        # Debug env loading (show only first few chars)
        api_key = settings.GROQ_API_KEY or ""
        if api_key:
            app_logger.info(
                "Groq API key loaded",
                groq_api_key_prefix=api_key[:6] + "…",
                groq_model=settings.GROQ_MODEL
            )
        else:
            app_logger.warning(
                "No Groq API key found - set GROQ_API_KEY environment variable"
            )

        app_logger.info(
            f"AI Product Manager starting up",
            version=settings.APP_VERSION,
            debug=settings.DEBUG,
            host=settings.HOST,
            port=settings.PORT
        )
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        app_logger.info("AI Product Manager shutting down")
    
    return app


# Create application instance
app = create_application()
