import json
import os
import google.generativeai as genai
from typing import Dict, Any
import os
from dotenv import load_dotenv
load_dotenv()
from schemas.planner import ProductVision


class PlannerAgent:
    """Planner Agent for generating product vision"""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.llm = genai.GenerativeModel("gemini-1.0-pro")
        self.prompt = """You are a senior Product Strategist.

Analyze the product idea and extract structured product vision.

Return ONLY JSON:
{
"product_name": "",
"problem_statement": "",
"target_users": [],
"core_goals": [],
"key_features_high_level": []
}

Do NOT include technical details. Be specific and concise."""
    
    def generate_vision(self, product_idea: str) -> ProductVision:
        """Generate product vision from idea"""
        try:
            full_prompt = f"{self.prompt}\n\nProduct Idea: {product_idea}"
            
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
            return ProductVision(**data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from Planner Agent: {e}\nContent: {content}")
        except Exception as e:
            raise RuntimeError(f"Error in Planner Agent: {e}")
    
    async def generate_vision_async(self, product_idea: str) -> ProductVision:
        """Async version of generate_vision"""
        return self.generate_vision(product_idea)
