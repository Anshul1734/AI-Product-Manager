"""
Enhanced agent classes with validation and retry logic for reliable outputs.
"""
from typing import Dict, Any, Optional
import json
import time
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
from langchain_core.output_parsers import PydanticOutputParser
from schemas.agent_validation import (
    AgentValidationFactory,
    create_fallback_output,
    ProductVision,
    PRD,
    SystemArchitecture,
    Tickets
)
from utils.logging import logger


class ValidatedPlannerAgent:
    """Enhanced Planner Agent with validation and retry logic"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.max_retries = 2
        
    def _create_prompt(self, product_idea: str) -> str:
        """Create a structured prompt for the planner agent"""
        return f"""
You are a Product Planning AI assistant. Your task is to analyze the given product idea and create a comprehensive product vision.

PRODUCT IDEA: {product_idea}

Please respond with a JSON object containing:
- product_name: A clear, compelling name for the product
- problem_statement: A concise description of the problem this product solves
- target_users: A list of target user groups (3-5 items)
- core_goals: A list of primary goals the product aims to achieve (3-5 items)
- key_features_high_level: A list of key features at a high level (3-5 items)

REQUIREMENTS:
- product_name: 3-100 characters, clear and descriptive
- problem_statement: 10-500 characters, specific and actionable
- target_users: 1-10 items, realistic user groups
- core_goals: 1-10 items, measurable and achievable
- key_features_high_level: 1-10 items, distinct and valuable

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.

Example format:
{{
    "product_name": "AI Project Manager",
    "problem_statement": "Teams struggle with project coordination and deadline tracking...",
    "target_users": ["Project Managers", "Development Teams", "Stakeholders"],
    "core_goals": ["Streamline project workflows", "Improve team communication", "Track progress accurately"],
    "key_features_high_level": ["AI-powered task scheduling", "Real-time collaboration", "Automated reporting"]
}}
"""
    
    def execute(self, product_idea: str) -> Dict[str, Any]:
        """Execute the planner agent with validation and retry logic"""
        logger.info("🤖 EXECUTING VALIDATED PLANNER AGENT")
        
        for attempt in range(self.max_retries + 1):
            try:
                # Generate response
                prompt = self._create_prompt(product_idea)
                messages = [
                    SystemMessage(content="You are a product planning expert who always responds with valid JSON."),
                    HumanMessage(content=prompt)
                ]
                
                start_time = time.time()
                response = self.model.generate_content(full_prompt)
                execution_time = time.time() - start_time
                
                raw_output = response.text
                logger.info(f"   Raw output (attempt {attempt + 1}): {raw_output[:200]}...")
                
                # Validate the output
                validated_output = AgentValidationFactory.validate_agent_output(
                    'planner', raw_output
                )
                
                logger.info(f"   ✅ Planner completed in {execution_time:.2f}s")
                logger.info(f"   📋 Generated: {validated_output['product_name']}")
                
                return validated_output
                
            except Exception as e:
                logger.warning(f"   ❌ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries:
                    logger.info(f"   🔄 Retrying... ({self.max_retries - attempt} attempts remaining)")
                    time.sleep(1)  # Brief pause before retry
                else:
                    logger.error(f"   🚨 All attempts failed, using fallback output")
                    return create_fallback_output('planner')
        
        # This should never be reached
        return create_fallback_output('planner')


class ValidatedAnalystAgent:
    """Enhanced Analyst Agent with validation and retry logic"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.max_retries = 2
        
    def _create_prompt(self, product_vision: Dict[str, Any]) -> str:
        """Create a structured prompt for the analyst agent"""
        product_name = product_vision.get('product_name', 'Product')
        problem_statement = product_vision.get('problem_statement', 'Problem statement')
        target_users = product_vision.get('target_users', [])
        core_goals = product_vision.get('core_goals', [])
        
        return f"""
You are a Product Requirements Document (PRD) specialist. Your task is to create a comprehensive PRD based on the product vision.

PRODUCT VISION:
- Product Name: {product_name}
- Problem Statement: {problem_statement}
- Target Users: {', '.join(target_users)}
- Core Goals: {', '.join(core_goals)}

Please respond with a JSON object containing:
- problem_statement: Detailed problem statement (10-1000 characters)
- target_users: List of target user groups (1-10 items)
- user_personas: List of user personas with name, description, and pain points (1-10 personas)
- user_stories: List of user stories with title, as_a, i_want_to, so_that (1-20 stories)
- success_metrics: List of success metrics with name, description, and target (1-10 metrics)

REQUIREMENTS:
- problem_statement: Detailed and specific
- target_users: Realistic user groups
- user_personas: Each with name (2-50 chars), description (10-200 chars), pain points (1-10 items)
- user_stories: Each with title (5-100 chars), as_a (3-100 chars), i_want_to (5-100 chars), so_that (5-200 chars)
- success_metrics: Each with name (3-50 chars), description (5-200 chars), target (1-50 chars)

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.

Example format:
{{
    "problem_statement": "Development teams struggle with...",
    "target_users": ["Software Developers", "Project Managers"],
    "user_personas": [{{
        "name": "Alex Developer",
        "description": "Senior developer working on multiple projects",
        "pain_points": ["Context switching", "Missing deadlines"]
    }}],
    "user_stories": [{{
        "title": "Task Management",
        "as_a": "developer",
        "i_want_to": "organize my tasks efficiently",
        "so_that": "I can meet my deadlines"
    }}],
    "success_metrics": [{{
        "name": "Productivity Increase",
        "description": "Measure of task completion efficiency",
        "target": "25% improvement"
    }}]
}}
"""
    
    def execute(self, product_vision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the analyst agent with validation and retry logic"""
        logger.info("🤖 EXECUTING VALIDATED ANALYST AGENT")
        
        for attempt in range(self.max_retries + 1):
            try:
                # Generate response
                prompt = self._create_prompt(product_vision)
                messages = [
                    SystemMessage(content="You are a PRD specialist who always responds with valid JSON."),
                    HumanMessage(content=prompt)
                ]
                
                start_time = time.time()
                response = self.model.generate_content(full_prompt)
                execution_time = time.time() - start_time
                
                raw_output = response.text
                logger.info(f"   Raw output (attempt {attempt + 1}): {raw_output[:200]}...")
                
                # Validate the output
                validated_output = AgentValidationFactory.validate_agent_output(
                    'analyst', raw_output
                )
                
                logger.info(f"   ✅ Analyst completed in {execution_time:.2f}s")
                logger.info(f"   👥 Target Users: {len(validated_output['target_users'])} groups")
                logger.info(f"   📝 User Stories: {len(validated_output['user_stories'])} stories")
                
                return validated_output
                
            except Exception as e:
                logger.warning(f"   ❌ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries:
                    logger.info(f"   🔄 Retrying... ({self.max_retries - attempt} attempts remaining)")
                    time.sleep(1)
                else:
                    logger.error(f"   🚨 All attempts failed, using fallback output")
                    return create_fallback_output('analyst')
        
        return create_fallback_output('analyst')


class ValidatedArchitectAgent:
    """Enhanced Architect Agent with validation and retry logic"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.max_retries = 2
        
    def _create_prompt(self, prd: Dict[str, Any]) -> str:
        """Create a structured prompt for the architect agent"""
        problem_statement = prd.get('problem_statement', 'Problem statement')
        target_users = prd.get('target_users', [])
        user_stories = prd.get('user_stories', [])
        
        return f"""
You are a System Architecture specialist. Your task is to design a comprehensive system architecture based on the PRD.

PRODUCT REQUIREMENTS:
- Problem Statement: {problem_statement}
- Target Users: {', '.join(target_users)}
- User Stories: {len(user_stories)} stories defined

Please respond with a JSON object containing:
- system_design: High-level system architecture description (10-500 characters)
- tech_stack: Dictionary of technology choices (1-10 items)
- architecture_components: List of system components (1-20 items)
- api_endpoints: List of API endpoints with name, method, endpoint, description (1-20 endpoints)
- database_schema: List of database tables with table_name and fields (1-10 tables)

REQUIREMENTS:
- system_design: Clear and comprehensive architecture overview
- tech_stack: Key technologies (frontend, backend, database, etc.)
- architecture_components: Distinct system components
- api_endpoints: Each with name, method (GET/POST/PUT/DELETE/PATCH), endpoint (starts with /), description
- database_schema: Each table with valid table_name and fields (each with name, type, constraints, at least one PRIMARY KEY)

Valid field types: UUID, TEXT, VARCHAR, INTEGER, BOOLEAN, TIMESTAMP, JSON, DECIMAL
Valid constraints: PRIMARY KEY, NOT NULL, UNIQUE, FOREIGN KEY, DEFAULT

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.

Example format:
{{
    "system_design": "Microservices architecture with...",
    "tech_stack": {{
        "frontend": "React with TypeScript",
        "backend": "FastAPI with Python",
        "database": "PostgreSQL with Redis cache"
    }},
    "architecture_components": ["API Gateway", "Authentication Service", "Database Layer"],
    "api_endpoints": [{{
        "name": "Generate Product Plan",
        "method": "POST",
        "endpoint": "/api/v1/generate",
        "description": "Generate comprehensive product plan"
    }}],
    "database_schema": [{{
        "table_name": "product_plans",
        "fields": [{{
            "name": "id",
            "type": "UUID",
            "constraints": "PRIMARY KEY"
        }}]
    }}]
}}
"""
    
    def execute(self, prd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the architect agent with validation and retry logic"""
        logger.info("🤖 EXECUTING VALIDATED ARCHITECT AGENT")
        
        for attempt in range(self.max_retries + 1):
            try:
                # Generate response
                prompt = self._create_prompt(prd)
                messages = [
                    SystemMessage(content="You are a system architecture expert who always responds with valid JSON."),
                    HumanMessage(content=prompt)
                ]
                
                start_time = time.time()
                response = self.model.generate_content(full_prompt)
                execution_time = time.time() - start_time
                
                raw_output = response.text
                logger.info(f"   Raw output (attempt {attempt + 1}): {raw_output[:200]}...")
                
                # Validate the output
                validated_output = AgentValidationFactory.validate_agent_output(
                    'architect', raw_output
                )
                
                logger.info(f"   ✅ Architect completed in {execution_time:.2f}s")
                logger.info(f"   🏗️  Architecture: {validated_output['system_design']}")
                logger.info(f"   📦 Components: {len(validated_output['architecture_components'])} services")
                
                return validated_output
                
            except Exception as e:
                logger.warning(f"   ❌ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries:
                    logger.info(f"   🔄 Retrying... ({self.max_retries - attempt} attempts remaining)")
                    time.sleep(1)
                else:
                    logger.error(f"   🚨 All attempts failed, using fallback output")
                    return create_fallback_output('architect')
        
        return create_fallback_output('architect')


class ValidatedTicketGeneratorAgent:
    """Enhanced Ticket Generator Agent with validation and retry logic"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.max_retries = 2
        
    def _create_prompt(self, prd: Dict[str, Any], architecture: Dict[str, Any]) -> str:
        """Create a structured prompt for the ticket generator agent"""
        problem_statement = prd.get('problem_statement', 'Problem statement')
        user_stories = prd.get('user_stories', [])
        tech_stack = architecture.get('tech_stack', {})
        api_endpoints = architecture.get('api_endpoints', [])
        
        return f"""
You are a Jira/Ticket Management specialist. Your task is to create comprehensive development tickets based on the PRD and system architecture.

REQUIREMENTS:
- Problem Statement: {problem_statement}
- User Stories: {len(user_stories)} stories defined
- Tech Stack: {', '.join(tech_stack.keys())}
- API Endpoints: {len(api_endpoints)} endpoints defined

Please respond with a JSON object containing:
- epics: List of epics with epic_name, description, and stories (1-10 epics)

Each epic should contain:
- epic_name: Clear epic name (3-100 characters)
- description: Epic description (5-500 characters)
- stories: List of user stories (1-10 stories per epic)

Each story should contain:
- story_title: Story title (3-100 characters)
- description: Story description (5-500 characters)
- acceptance_criteria: List of acceptance criteria (1-10 items)
- tasks: List of development tasks (1-20 tasks per story)

Each task should contain:
- title: Task title (3-100 characters)
- description: Task description (5-500 characters)
- estimated_hours: Estimated hours in decimal format (0.5-100)

REQUIREMENTS:
- All strings must be non-empty and within character limits
- All lists must have the required minimum number of items
- Estimated hours must be valid decimal numbers between 0.5 and 100
- Acceptance criteria should be specific and testable

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.

Example format:
{{
    "epics": [{{
        "epic_name": "Core Product Planning",
        "description": "Implement the main product planning functionality",
        "stories": [{{
            "story_title": "User Input Processing",
            "description": "Process and validate user product ideas",
            "acceptance_criteria": ["User can input product idea", "System validates input"],
            "tasks": [{{
                "title": "Create input form",
                "description": "Design and implement the input form",
                "estimated_hours": "8"
            }}]
        }}]
    }}]
}}
"""
    
    def execute(self, prd: Dict[str, Any], architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ticket generator agent with validation and retry logic"""
        logger.info("🤖 EXECUTING VALIDATED TICKET GENERATOR AGENT")
        
        for attempt in range(self.max_retries + 1):
            try:
                # Generate response
                prompt = self._create_prompt(prd, architecture)
                messages = [
                    SystemMessage(content="You are a ticket management expert who always responds with valid JSON."),
                    HumanMessage(content=prompt)
                ]
                
                start_time = time.time()
                response = self.model.generate_content(full_prompt)
                execution_time = time.time() - start_time
                
                raw_output = response.text
                logger.info(f"   Raw output (attempt {attempt + 1}): {raw_output[:200]}...")
                
                # Validate the output
                validated_output = AgentValidationFactory.validate_agent_output(
                    'ticket_generator', raw_output
                )
                
                logger.info(f"   ✅ Ticket Generator completed in {execution_time:.2f}s")
                logger.info(f"   📋 Epics: {len(validated_output['epics'])}")
                
                total_stories = sum(len(epic['stories']) for epic in validated_output['epics'])
                logger.info(f"   📝 Stories: {total_stories}")
                
                total_tasks = sum(
                    len(story['tasks']) 
                    for epic in validated_output['epics'] 
                    for story in epic['stories']
                )
                logger.info(f"   ✅ Tasks: {total_tasks}")
                
                return validated_output
                
            except Exception as e:
                logger.warning(f"   ❌ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries:
                    logger.info(f"   🔄 Retrying... ({self.max_retries - attempt} attempts remaining)")
                    time.sleep(1)
                else:
                    logger.error(f"   🚨 All attempts failed, using fallback output")
                    return create_fallback_output('ticket_generator')
        
        return create_fallback_output('ticket_generator')


# ============================================================================
# VALIDATED WORKFLOW MANAGER
# ============================================================================

class ValidatedWorkflowManager:
    """Workflow manager with validated agents and comprehensive error handling"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.planner = ValidatedPlannerAgent(model_name)
        self.analyst = ValidatedAnalystAgent(model_name)
        self.architect = ValidatedArchitectAgent(model_name)
        self.ticket_generator = ValidatedTicketGeneratorAgent(model_name)
        
    def execute_workflow(self, product_idea: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute the complete workflow with validation and error handling"""
        logger.info(f"🚀 STARTING VALIDATED WORKFLOW EXECUTION")
        logger.info(f"   Product Idea: {product_idea[:100]}...")
        logger.info(f"   Thread ID: {thread_id}")
        
        start_time = time.time()
        agent_times = {}
        
        try:
            # Step 1: Planner Agent
            step_start = time.time()
            plan = self.planner.execute(product_idea)
            agent_times['planner'] = time.time() - step_start
            
            # Step 2: Analyst Agent
            step_start = time.time()
            prd = self.analyst.execute(plan)
            agent_times['analyst'] = time.time() - step_start
            
            # Step 3: Architect Agent
            step_start = time.time()
            architecture = self.architect.execute(prd)
            agent_times['architect'] = time.time() - step_start
            
            # Step 4: Ticket Generator Agent
            step_start = time.time()
            tickets = self.ticket_generator.execute(prd, architecture)
            agent_times['ticket_generator'] = time.time() - step_start
            
            # Combine results
            total_time = time.time() - start_time
            
            workflow_output = {
                'plan': plan,
                'prd': prd,
                'architecture': architecture,
                'tickets': tickets,
                'execution_time': total_time,
                'agent_times': agent_times,
                'thread_id': thread_id or f"thread_{int(time.time())}"
            }
            
            logger.info(f"✅ VALIDATED WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info(f"📊 EXECUTION SUMMARY:")
            logger.info(f"   - Total Time: {total_time:.2f}s")
            for agent, time_taken in agent_times.items():
                logger.info(f"   - {agent.title()}: {time_taken:.2f}s")
            
            return workflow_output
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ VALIDATED WORKFLOW FAILED")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Execution Time: {total_time:.2f}s")
            
            # Return error response with fallback data
            return {
                'success': False,
                'error': str(e),
                'execution_time': total_time,
                'thread_id': thread_id,
                'fallback_data': {
                    'plan': create_fallback_output('planner'),
                    'prd': create_fallback_output('analyst'),
                    'architecture': create_fallback_output('architect'),
                    'tickets': create_fallback_output('ticket_generator')
                }
            }
