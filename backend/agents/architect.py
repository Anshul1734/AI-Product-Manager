import json
import os
import google.generativeai as genai
from typing import Dict, Any
import os
from dotenv import load_dotenv
load_dotenv()
from schemas.architect import SystemArchitecture
from schemas.analyst import PRD


class ArchitectAgent:
    """Tech Architect Agent for generating system architecture"""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.llm = genai.GenerativeModel("gemini-1.0-pro")
        self.prompt = """You are a senior Software Architect.

Input: PRD JSON.

Return ONLY JSON:
{
"system_design": "",
"tech_stack": {
"frontend": "",
"backend": "",
"database": "",
"infrastructure": ""
},
"architecture_components": [],
"api_endpoints": [
{
"name": "",
"method": "",
"endpoint": "",
"description": ""
}
],
"database_schema": [
{
"table_name": "",
"fields": [
{
"name": "",
"type": "",
"constraints": ""
}
]
}
]
}

Ensure realistic, scalable design with modern stack."""
    
    def generate_architecture(self, prd: PRD) -> SystemArchitecture:
        """Generate system architecture from PRD"""
        try:
            prd_json = prd.model_dump_json(indent=2)
            
            full_prompt = f"{self.prompt}\n\nPRD:\n{prd_json}"
            
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
            return SystemArchitecture(**data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from Architect Agent: {e}\nContent: {content}")
        except Exception as e:
            raise RuntimeError(f"Error in Architect Agent: {e}")
    
    async def generate_architecture_async(self, prd: PRD) -> SystemArchitecture:
        """Async version of generate_architecture"""
        return self.generate_architecture(prd)
