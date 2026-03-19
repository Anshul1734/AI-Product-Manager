import json
import os
import google.generativeai as genai
from typing import Dict, Any
import os
from dotenv import load_dotenv
load_dotenv()
from schemas.ticket_generator import Tickets
from schemas.analyst import PRD
from schemas.architect import SystemArchitecture


class TicketGeneratorAgent:
    """Ticket Generator Agent for creating Jira-style tickets"""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.llm = genai.GenerativeModel("gemini-1.0-pro")
        self.prompt = """You are a senior Engineering Manager.

Input: PRD + Architecture JSON.

Return ONLY JSON:
{
"epics": [
{
"epic_name": "",
"description": "",
"stories": [
{
"story_title": "",
"description": "",
"acceptance_criteria": [],
"tasks": [
{
"title": "",
"description": "",
"estimated_hours": ""
}
]
}
]
}
]
}

Break into clear epics, stories, and actionable tasks."""
    
    def generate_tickets(self, prd: PRD, architecture: SystemArchitecture) -> Tickets:
        """Generate Jira-style tickets from PRD and architecture"""
        try:
            prd_json = prd.model_dump_json(indent=2)
            arch_json = architecture.model_dump_json(indent=2)
            
            full_prompt = f"{self.prompt}\n\nPRD:\n{prd_json}\n\nArchitecture:\n{arch_json}"
            
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
            return Tickets(**data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from Ticket Generator Agent: {e}\nContent: {content}")
        except Exception as e:
            raise RuntimeError(f"Error in Ticket Generator Agent: {e}")
    
    async def generate_tickets_async(self, prd: PRD, architecture: SystemArchitecture) -> Tickets:
        """Async version of generate_tickets"""
        return self.generate_tickets(prd, architecture)
