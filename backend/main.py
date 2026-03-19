from dotenv import load_dotenv
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load environment variables first
# Force reload for groq key
load_dotenv(override=True)
print("GROQ KEY LOADED:", bool(os.getenv("GROQ_API_KEY")))

app = FastAPI(
    title="AI Product Manager Agent",
    description="Backend for AI Product Manager Agent using Groq",
    version="1.0.0"
)

# Configure CORS allowing deployed frontend
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True, # Need to be careful here if adding "*" to cors_origins
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate")
async def generate(data: dict):
    idea = data.get("idea")
    print("Request received:", idea)
    
    if not idea:
        return {"success": False, "error": "No idea provided"}

    try:
        print("Calling Groq...")
        from product_service import generate_product_plan
        result = generate_product_plan(idea)
        print("Response received")

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        print("Error during generation:", str(e))
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
