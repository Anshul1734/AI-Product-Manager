import json
import os
import google.generativeai as genai
from typing import Dict, Any
import os
from dotenv import load_dotenv
load_dotenv()
from schemas.analyst import PRD
from schemas.planner import ProductVision


class AnalystAgent:
    """Analyst Agent for generating PRD"""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.llm = genai.GenerativeModel("gemini-1.0-pro")
        self.prompt = """You are a senior Product Analyst writing a PRD.

Input: structured product vision.

Return ONLY JSON:
{
"problem_statement": "",
"target_users": [],
"user_personas": [
{
"name": "",
"description": "",
"pain_points": []
}
],
"user_stories": [
{
"title": "",
"as_a": "",
"i_want_to": "",
"so_that": ""
}
],
"success_metrics": [
{
"name": "",
"description": "",
"target": ""
}
]
}

Write realistic personas and user stories in proper format."""
    
    def generate_prd(self, product_vision: ProductVision) -> PRD:
        """Generate PRD from product vision"""
        try:
            vision_json = product_vision.model_dump_json(indent=2)
            
            full_prompt = f"{self.prompt}\n\nProduct Vision:\n{vision_json}"
            
            response = self.llm.generate_content(full_prompt)
            content = response.text.strip()
            
            # Clean up response to ensure valid JSON
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON and validate
            data = json.loads(content)
            return PRD(**data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from Analyst Agent: {e}\nContent: {content}")
        except Exception as e:
            raise RuntimeError(f"Error in Analyst Agent: {e}")
    
    async def generate_prd_async(self, product_vision: ProductVision) -> PRD:
        """Async version of generate_prd"""
        return self.generate_prd(product_vision)
