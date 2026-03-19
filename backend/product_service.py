import requests
import os
import json

def call_llm(prompt: str):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise Exception("GROQ_API_KEY missing")
    
    api_key = api_key.strip().replace('"', '').replace("'", "")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Groq error: {response.text}")

    data = response.json()

    if "choices" not in data:
        raise Exception(f"Invalid response: {data}")

    return data["choices"][0]["message"]["content"]

def generate_product_plan(idea: str):
    prompt = f"""
    You are an expert AI Product Manager. Act as a professional product manager and generate a structured product plan for the following product idea:
    IDEA: {idea}
    
    You MUST respond with purely valid JSON matching the exact schema below. Use this exact structure:
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
        "user_personas": [{{"name": "string", "description": "string", "pain_points": ["string"]}}],
        "user_stories": [{{"title": "string", "as_a": "string", "i_want_to": "string", "so_that": "string"}}],
        "success_metrics": [{{"name": "string", "description": "string", "target": "string"}}]
      }},
      "architecture": {{
        "system_design": "string",
        "tech_stack": {{"frontend": "string", "backend": "string", "database": "string"}},
        "api_endpoints": ["string"],
        "architecture_components": ["string"],
        "database_schema": [{{"table_name": "string", "fields": [{{"name": "string", "type": "string", "constraints": "string"}}]}}]
      }},
      "tickets": {{
        "epics": [{{"epic_name": "string", "description": "string", "stories": [{{"story_title": "string", "description": "string", "acceptance_criteria": ["string"], "tasks": [{{"title": "string", "estimated_hours": 2}}]}}]}}]
      }}
    }}
    
    Ensure the output is ONLY valid JSON.
    """
    
    response_text = call_llm(prompt)
    
    try:
        # Guarantee JSON extraction even if LLM hallucinates preamble without markdown backticks
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            response_text = response_text[start_idx:end_idx+1]
            
        parsed_data = json.loads(response_text)
        return parsed_data
    except json.JSONDecodeError:
        # Fallback if the response is not perfectly formatted JSON
        return {
            "plan": {"description": response_text},
            "prd": {},
            "architecture": {},
            "tickets": {}
        }
