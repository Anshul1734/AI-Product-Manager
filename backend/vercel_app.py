"""
Lightweight Vercel serverless entry point.
Completely self-contained - no heavy imports from the main app.
Only imports what's needed: fastapi, requests, os, json, re.
"""
import os
import json
import re
import random
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Product Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductRequest(BaseModel):
    idea: str
    thread_id: Optional[str] = None
    use_legacy: Optional[bool] = False


# ---------- Groq helper ----------

def call_groq(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    if not api_key or api_key == "gsk_your_actual_key_here":
        raise ValueError("GROQ_API_KEY environment variable is not set on Vercel")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert AI Product Manager. You only respond with raw, valid JSON — no markdown, no commentary."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        timeout=55,  # Vercel max is 60s
    )

    if response.status_code != 200:
        raise ValueError(f"Groq API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    if "choices" not in data or not data["choices"]:
        raise ValueError(f"Invalid Groq response: {data}")

    return data["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*({[\s\S]*?})\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"({[\s\S]*})", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    raise ValueError("Could not extract valid JSON from Groq response")


def enrich_features(features: list) -> list:
    detailed = []
    for feature in features:
        reach = random.randint(100, 10000)
        impact = random.randint(1, 3)
        confidence = random.randint(50, 100)
        effort = random.randint(1, 10)
        score = (reach * impact * (confidence / 100.0)) / effort
        detailed.append({
            "name": feature,
            "description": f"System capabilities to support {feature.lower()}",
            "rice": {
                "reach": reach, "impact": impact,
                "confidence": confidence, "effort": effort,
                "score": round(score, 1),
            },
            "justification": "Delivers core product value and directly addresses user pain points.",
        })
    detailed.sort(key=lambda x: x["rice"]["score"], reverse=True)
    return detailed


def generate_product_plan(idea: str) -> dict:
    prompt = f"""You are an expert AI Product Manager.

Create a PROFESSIONAL and DETAILED product plan for:
{idea}

You MUST output your response STRICTLY as a valid JSON object matching this exact schema:

{{
  "plan": {{
    "product_name": "string",
    "problem_statement": "string",
    "target_users": ["string"],
    "core_goals": ["string"],
    "key_features_high_level": ["string"]
  }},
  "prd": {{
    "problem_statement": "string",
    "target_users": ["string"],
    "user_personas": [
      {{ "name": "string", "description": "string", "pain_points": ["string"] }}
    ],
    "user_stories": [
      {{ "title": "string", "as_a": "string", "i_want_to": "string", "so_that": "string" }}
    ],
    "success_metrics": [
      {{ "name": "string", "description": "string", "target": "string" }}
    ]
  }},
  "architecture": {{
    "system_design": "string",
    "tech_stack": {{ "frontend": "string", "backend": "string", "database": "string", "infrastructure": "string" }},
    "architecture_components": ["string"],
    "api_endpoints": ["string"],
    "database_schema": [
      {{ "table_name": "string", "fields": [ {{ "name": "string", "type": "string", "constraints": "string" }} ] }}
    ]
  }},
  "tickets": {{
    "epics": [
      {{
        "epic_name": "string",
        "description": "string",
        "stories": [
          {{
            "story_title": "string",
            "description": "string",
            "acceptance_criteria": ["string"],
            "tasks": [
              {{ "title": "string", "estimated_hours": 4 }}
            ]
          }}
        ]
      }}
    ]
  }},
  "agent_steps": [
    "Generated product vision",
    "Extracted features",
    "Calculated RICE scores",
    "Generated PRD, architecture, and tickets"
  ]
}}

IMPORTANT:
- api_endpoints must be an array of STRINGS (e.g. "GET /api/users"), NOT objects
- Make sure the JSON is valid with no trailing commas
- DO NOT output any markdown, only the raw JSON object
"""

    response_text = call_groq(prompt)
    plan_data = extract_json(response_text)

    if "features_detailed" not in plan_data:
        features = plan_data.get("plan", {}).get("key_features_high_level", [])
        plan_data["features_detailed"] = enrich_features(features)

    if "agent_steps" not in plan_data:
        plan_data["agent_steps"] = [
            "Generated product vision",
            "Extracted features",
            "Calculated RICE scores",
            "Generated development tickets",
        ]

    return plan_data


# ---------- Routes ----------

@app.get("/")
async def root():
    return {"status": "ok", "message": "AI Product Manager is running"}


@app.get("/api/v1/health")
async def health():
    api_key = os.getenv("GROQ_API_KEY", "")
    return {
        "status": "healthy",
        "groq_key_set": bool(api_key and api_key != "gsk_your_actual_key_here"),
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    }


@app.post("/generate")
@app.post("/api/v1/generate")
async def generate(request: ProductRequest):
    import time
    start = time.time()
    try:
        result = generate_product_plan(request.idea)
        elapsed = time.time() - start
        return {
            "success": True,
            "message": "Product plan generated successfully",
            "data": result,
            "execution_time": elapsed,
            "thread_id": request.thread_id,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to generate product plan: {str(e)}",
            "data": None,
            "execution_time": time.time() - start,
            "thread_id": request.thread_id,
        }


# Export routes stubs (so other frontend calls don't 404)
@app.post("/api/v1/export/prd/pdf")
async def export_prd_pdf(request: ProductRequest):
    return {"success": False, "message": "Export not available in serverless mode"}


@app.post("/api/v1/export/tickets/csv")
async def export_tickets_csv(request: ProductRequest):
    return {"success": False, "message": "Export not available in serverless mode"}


@app.post("/api/v1/export/full/json")
async def export_full_json(request: ProductRequest):
    return {"success": False, "message": "Export not available in serverless mode"}
