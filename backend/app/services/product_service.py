"""
Product plan generation service using Groq.
"""
from .groq_client import call_llm


def generate_product_plan(idea: str) -> str:
    """Generate a complete product plan using Groq."""
    prompt = f"""
You are an expert AI Product Manager.

Create a PROFESSIONAL and DETAILED product plan for:

{idea}

Structure output clearly with these sections:

1. Product Vision
   - Product name
   - Problem statement
   - Target users
   - Core goals
   - Value proposition

2. Target Users
   - Primary user groups
   - User demographics
   - User needs and pain points

3. User Personas
   - 2-3 detailed personas
   - Each with: name, role, goals, challenges

4. Core Features
   - Main features list
   - Feature descriptions
   - User stories for key features

5. Tech Stack
   - Recommended technologies
   - Framework choices
   - Database recommendations

6. System Architecture
   - High-level architecture
   - Component design
   - Data flow

7. API Endpoints
   - Key API endpoints
   - Request/response format
   - Authentication approach

8. Development Tickets
   - Epic breakdown
   - User stories with priority
   - Technical tasks

Make it structured, clean, and suitable for a real startup. Be detailed and actionable.
"""

    return call_llm(prompt, system_prompt="You are an expert AI Product Manager creating comprehensive product plans.")
