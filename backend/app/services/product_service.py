"""
Product plan generation service using Groq.
"""
import json
import re
import random
from .groq_client import call_llm

def enrich_features(features: list) -> list:
    """Enrich a list of basic features with generated RICE scores and justification."""
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
                "reach": reach,
                "impact": impact,
                "confidence": confidence,
                "effort": effort,
                "score": round(score, 1)
            },
            "justification": "Delivers core product value and directly addresses user pain points."
        })
    # Sort descending by score
    detailed.sort(key=lambda x: x["rice"]["score"], reverse=True)
    return detailed

def extract_json(text: str) -> dict:
    """Extract JSON from text that might contain markdown formatting."""
    try:
        # First try direct parsing
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in markdown blocks
    match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Try finding anything that looks like a JSON object
    match = re.search(r'({[\s\S]*})', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    raise ValueError("Could not extract valid JSON from the response.")


def generate_product_plan(idea: str) -> dict:
    """Generate a complete product plan using Groq, formatted as JSON to match frontend expectations."""
    prompt = f"""
You are an expert AI Product Manager.

Create a PROFESSIONAL and DETAILED product plan for:

{idea}

Follow these exact steps internally to build your response:
Step 1: Generate product vision.
Step 2: Extract a distinct list of core features.
Step 3: Enrich each feature by estimating its RICE score:
  - reach: estimated number of users (100–10000)
  - impact: 1 (low), 2 (medium), 3 (high)
  - confidence: 50–100
  - effort: 1–10
  - score = (reach * impact * confidence/100) / effort
  - Justification: Explain impact on user & business value (1-2 lines max).
  Sort features descending by RICE score.
Step 4: Generate PRD.
Step 5: Generate architecture.
Step 6: Generate tickets.

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
    "api_endpoints": [
      {{ "name": "string", "method": "string", "endpoint": "string", "description": "string" }}
    ],
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
              {{ "title": "string", "description": "string", "estimated_hours": "string" }}
            ]
          }}
        ]
      }}
    ]
  }},
  "features_detailed": [
    {{
      "name": "string",
      "description": "string",
      "rice": {{
        "reach": 0,
        "impact": 0,
        "confidence": 0,
        "effort": 0,
        "score": 0.0
      }},
      "justification": "string"
    }}
  ],
  "agent_steps": [
    "Generated product vision",
    "Extracted features",
    "Calculated RICE scores",
    "Generated PRD, architecture, and tickets"
  ]
}}

Make sure the JSON is properly escaped and does not contain trailing commas.
DO NOT output any markdown, only the raw JSON object.
"""

    response_text = call_llm(prompt, system_prompt="You are an expert AI Product Manager creating comprehensive product plans. You only respond with raw, valid JSON.")
    
    # Try to extract and return JSON
    try:
        plan_data = extract_json(response_text)
        
        # Post-processing wrapper: ensure agent features exist
        if "features_detailed" not in plan_data:
            features = plan_data.get("plan", {}).get("key_features_high_level", [])
            plan_data["features_detailed"] = enrich_features(features)
            
        if "agent_steps" not in plan_data:
            plan_data["agent_steps"] = [
                "Generated product vision",
                "Extracted features",
                "Calculated RICE scores",
                "Generated development tickets"
            ]
            
        print("===== FINAL API RESPONSE LOG =====")
        try:
            print(json.dumps(plan_data, indent=2)[:800] + "\n... [truncated] ...\n" + json.dumps({"features_detailed": plan_data.get("features_detailed"), "agent_steps": plan_data.get("agent_steps")}, indent=2))
        except Exception:
            pass
        print("==================================")
            
        return plan_data
    except ValueError as e:
        # Fallback to basic dictionary if parsing fails
        print(f"Failed to parse Groq response: {e}")
        with open("error_trace.txt", "w", encoding="utf-8") as f:
            f.write(response_text)
            
        return {
            "plan": {
                "product_name": "Fallback Plan",
                "problem_statement": "Could not generate product plan due to parsing errors.",
                "target_users": ["Everyone"],
                "core_goals": ["Fix the JSON generation"],
                "key_features_high_level": ["Fallback feature"]
            },
            "prd": {
                "problem_statement": "Parsing Error",
                "target_users": ["Everyone"],
                "user_personas": [],
                "user_stories": [],
                "success_metrics": []
            },
            "architecture": {
                "system_design": "Basic",
                "tech_stack": {"frontend": "React", "backend": "Node", "database": "SQL", "infrastructure": "Cloud"},
                "architecture_components": [],
                "api_endpoints": [],
                "database_schema": []
            },
            "tickets": {
                "epics": []
            },
            "features_detailed": [
                {
                    "name": "Fallback Feature",
                    "description": "This feature loaded from a fallback",
                    "rice": {"reach": 100, "impact": 1, "confidence": 50, "effort": 5, "score": 10.0},
                    "justification": "Provides testing ground for errors"
                }
            ],
            "agent_steps": ["Attempted Generation", "Failed JSON Parsing"]
        }

