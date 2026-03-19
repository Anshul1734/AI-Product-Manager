"""
Memory-aware agents that can use previous conversation context for better responses.
"""
from typing import Dict, Any, List, Optional
import json
import time
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
from memory.memory_store import get_memory_store, create_memory_entry
from utils.logging import logger


class MemoryAwarePlannerAgent:
    """Planner agent with memory awareness for context reuse"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.memory_store = get_memory_store()
        
    def _create_context_aware_prompt(self, product_idea: str, thread_id: str) -> str:
        """Create a prompt that includes relevant context from memory"""
        
        # Get relevant context
        context = self.memory_store.get_relevant_context(thread_id, product_idea)
        
        # Build context sections
        context_sections = []
        
        # Thread history
        if context['thread_history']:
            context_sections.append("PREVIOUS CONVERSATION HISTORY:")
            for entry in context['thread_history'][-2:]:  # Last 2 entries
                context_sections.append(f"- Previous Idea: {entry['product_idea']}")
                if 'plan' in entry['workflow_output']:
                    plan = entry['workflow_output']['plan']
                    context_sections.append(f"  Previous Product: {plan.get('product_name', 'N/A')}")
                    context_sections.append(f"  Previous Problem: {plan.get('problem_statement', 'N/A')[:100]}...")
        
        # Similar ideas
        if context['similar_ideas']:
            context_sections.append("\nSIMILAR PRODUCT IDEAS:")
            for similar in context['similar_ideas'][:2]:  # Top 2 similar
                entry = similar['entry']
                similarity = similar['similarity']
                context_sections.append(f"- Similar Idea ({similarity:.2f} similarity): {entry['product_idea']}")
                
                # Add relevant insights
                if similar['relevant_insights']:
                    context_sections.append(f"  Insights: {', '.join(similar['relevant_insights'])}")
        
        # Thread summary
        if context['thread_summary']:
            summary = context['thread_summary']
            context_sections.append(f"\nCONVERSATION SUMMARY:")
            context_sections.append(f"- Topics: {', '.join(summary.get('topics', []))}")
            context_sections.append(f"- Previous Quality: {summary.get('average_quality', 'N/A')}")
            if summary.get('key_insights'):
                context_sections.append(f"- Key Insights: {summary['key_insights'][0]}")
        
        # Build full prompt
        context_text = "\n".join(context_sections) if context_sections else "No previous context available."
        
        return f"""
You are a Product Planning AI assistant with access to previous conversation context. Your task is to analyze the given product idea and create a comprehensive product vision, leveraging relevant insights from previous conversations when helpful.

CONTEXT INFORMATION:
{context_text}

CURRENT PRODUCT IDEA:
{product_idea}

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

CONTEXT GUIDELINES:
- If similar ideas exist, consider what worked well before
- Build upon previous successful patterns when relevant
- Avoid repeating exact same approaches for similar ideas
- Learn from previous quality issues and improve
- Consider the conversation's established themes and topics

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
    
    def execute(self, product_idea: str, thread_id: str) -> Dict[str, Any]:
        """Execute the planner agent with memory awareness"""
        logger.info(f"🧠 EXECUTING MEMORY-AWARE PLANNER AGENT")
        logger.info(f"   Thread ID: {thread_id}")
        logger.info(f"   Product Idea: {product_idea[:100]}...")
        
        try:
            # Generate context-aware response
            prompt = self._create_context_aware_prompt(product_idea, thread_id)
            messages = [
                SystemMessage(content="You are a product planning expert with memory of previous conversations."),
                HumanMessage(content=prompt)
            ]
            
            start_time = time.time()
            response = self.model.generate_content(full_prompt)
            execution_time = time.time() - start_time
            
            raw_output = response.text
            logger.info(f"   Raw output generated in {execution_time:.2f}s")
            
            # Validate the output
            from schemas.agent_validation import AgentValidationFactory
            validated_output = AgentValidationFactory.validate_agent_output(
                'planner', raw_output
            )
            
            logger.info(f"   ✅ Memory-aware planner completed")
            logger.info(f"   📋 Generated: {validated_output['product_name']}")
            
            return validated_output
            
        except Exception as e:
            logger.error(f"   ❌ Memory-aware planner failed: {str(e)}")
            # Fallback to non-memory-aware approach
            return self._execute_fallback(product_idea)
    
    def _execute_fallback(self, product_idea: str) -> Dict[str, Any]:
        """Fallback execution without memory"""
        logger.warning("   🔄 Using fallback execution without memory")
        
        # Simple fallback prompt
        prompt = f"""
Create a product vision for: {product_idea}

Respond with JSON containing product_name, problem_statement, target_users, core_goals, key_features_high_level.
"""
        
        try:
            messages = [
                SystemMessage(content="You are a product planning expert."),
                HumanMessage(content=prompt)
            ]
            
            response = self.model.generate_content(full_prompt)
            raw_output = response.text
            
            from schemas.agent_validation import AgentValidationFactory
            validated_output = AgentValidationFactory.validate_agent_output(
                'planner', raw_output
            )
            
            return validated_output
            
        except Exception as e:
            logger.error(f"   ❌ Fallback execution failed: {str(e)}")
            from schemas.agent_validation import create_fallback_output
            return create_fallback_output('planner')


class MemoryAwareAnalystAgent:
    """Analyst agent with memory awareness"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.memory_store = get_memory_store()
    
    def execute(self, product_vision: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """Execute the analyst agent with memory awareness"""
        logger.info(f"🧠 EXECUTING MEMORY-AWARE ANALYST AGENT")
        logger.info(f"   Thread ID: {thread_id}")
        
        try:
            # Get context for this thread
            context = self.memory_store.get_relevant_context(thread_id, product_vision.get('product_name', ''))
            
            # Create context-aware prompt
            prompt = self._create_context_aware_prompt(product_vision, context)
            
            messages = [
                SystemMessage(content="You are a PRD specialist with memory of previous conversations."),
                HumanMessage(content=prompt)
            ]
            
            start_time = time.time()
            response = self.model.generate_content(full_prompt)
            execution_time = time.time() - start_time
            
            raw_output = response.text
            logger.info(f"   Raw output generated in {execution_time:.2f}s")
            
            # Validate the output
            from schemas.agent_validation import AgentValidationFactory
            validated_output = AgentValidationFactory.validate_agent_output(
                'analyst', raw_output
            )
            
            logger.info(f"   ✅ Memory-aware analyst completed")
            logger.info(f"   👥 User Personas: {len(validated_output['user_personas'])}")
            
            return validated_output
            
        except Exception as e:
            logger.error(f"   ❌ Memory-aware analyst failed: {str(e)}")
            from schemas.agent_validation import create_fallback_output
            return create_fallback_output('analyst')
    
    def _create_context_aware_prompt(self, product_vision: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create context-aware prompt for analyst"""
        
        context_sections = []
        
        # Previous user personas
        if context['thread_history']:
            context_sections.append("PREVIOUS USER PERSONAS:")
            for entry in context['thread_history'][-1:]:  # Last entry
                if 'prd' in entry['workflow_output']:
                    prd = entry['workflow_output']['prd']
                    if 'user_personas' in prd:
                        for persona in prd['user_personas'][:2]:
                            context_sections.append(f"- {persona.get('name', 'N/A')}: {persona.get('description', 'N/A')[:80]}...")
        
        # Similar user types
        if context['similar_ideas']:
            context_sections.append("\nSIMILAR PRODUCT USER TYPES:")
            for similar in context['similar_ideas'][:1]:
                entry = similar['entry']
                if 'prd' in entry['workflow_output']:
                    prd = entry['workflow_output']['prd']
                    if 'target_users' in prd:
                        context_sections.append(f"- Target Users: {', '.join(prd['target_users'])}")
        
        context_text = "\n".join(context_sections) if context_sections else "No previous context available."
        
        product_name = product_vision.get('product_name', 'Product')
        problem_statement = product_vision.get('problem_statement', 'Problem statement')
        target_users = product_vision.get('target_users', [])
        core_goals = product_vision.get('core_goals', [])
        
        return f"""
You are a Product Requirements Document (PRD) specialist with access to previous conversation context. Your task is to create a comprehensive PRD based on the product vision, leveraging insights from previous similar products.

CONTEXT INFORMATION:
{context_text}

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

CONTEXT GUIDELINES:
- Consider previous user personas that worked well
- Build upon successful user story patterns
- Learn from previous target user definitions
- Maintain consistency with established user types

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.
"""
    
    def _execute_fallback(self, product_vision: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback execution without memory"""
        from schemas.agent_validation import create_fallback_output
        return create_fallback_output('analyst')


class MemoryAwareArchitectAgent:
    """Architect agent with memory awareness"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.memory_store = get_memory_store()
    
    def execute(self, prd: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """Execute the architect agent with memory awareness"""
        logger.info(f"🧠 EXECUTING MEMORY-AWARE ARCHITECT AGENT")
        logger.info(f"   Thread ID: {thread_id}")
        
        try:
            # Get context
            context = self.memory_store.get_relevant_context(thread_id, prd.get('problem_statement', ''))
            
            # Create context-aware prompt
            prompt = self._create_context_aware_prompt(prd, context)
            
            messages = [
                SystemMessage(content="You are a system architecture expert with memory of previous conversations."),
                HumanMessage(content=prompt)
            ]
            
            start_time = time.time()
            response = self.model.generate_content(full_prompt)
            execution_time = time.time() - start_time
            
            raw_output = response.text
            logger.info(f"   Raw output generated in {execution_time:.2f}s")
            
            # Validate the output
            from schemas.agent_validation import AgentValidationFactory
            validated_output = AgentValidationFactory.validate_agent_output(
                'architect', raw_output
            )
            
            logger.info(f"   ✅ Memory-aware architect completed")
            logger.info(f"   🏗️  Architecture: {validated_output['system_design']}")
            
            return validated_output
            
        except Exception as e:
            logger.error(f"   ❌ Memory-aware architect failed: {str(e)}")
            from schemas.agent_validation import create_fallback_output
            return create_fallback_output('architect')
    
    def _create_context_aware_prompt(self, prd: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create context-aware prompt for architect"""
        
        context_sections = []
        
        # Previous tech stacks
        if context['thread_history']:
            context_sections.append("PREVIOUS TECHNICAL APPROACHES:")
            for entry in context['thread_history'][-1:]:
                if 'architecture' in entry['workflow_output']:
                    arch = entry['workflow_output']['architecture']
                    if 'tech_stack' in arch:
                        tech_stack = list(arch['tech_stack'].keys())
                        context_sections.append(f"- Previous Tech Stack: {', '.join(tech_stack)}")
                    if 'system_design' in arch:
                        context_sections.append(f"- Previous Design: {arch['system_design'][:100]}...")
        
        # Similar architectures
        if context['similar_ideas']:
            context_sections.append("\nSIMILAR PRODUCT ARCHITECTURES:")
            for similar in context['similar_ideas'][:1]:
                entry = similar['entry']
                if 'architecture' in entry['workflow_output']:
                    arch = entry['workflow_output']['architecture']
                    if 'architecture_components' in arch:
                        components = arch['architecture_components'][:3]
                        context_sections.append(f"- Components: {', '.join(components)}")
        
        context_text = "\n".join(context_sections) if context_sections else "No previous context available."
        
        problem_statement = prd.get('problem_statement', 'Problem statement')
        target_users = prd.get('target_users', [])
        user_stories = prd.get('user_stories', [])
        
        return f"""
You are a System Architecture specialist with access to previous conversation context. Your task is to design a comprehensive system architecture based on the PRD, leveraging insights from previous similar solutions.

CONTEXT INFORMATION:
{context_text}

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

CONTEXT GUIDELINES:
- Consider previous successful tech stacks
- Build upon proven architectural patterns
- Learn from previous component choices
- Maintain consistency with established approaches

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.
"""
    
    def _execute_fallback(self, prd: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback execution without memory"""
        from schemas.agent_validation import create_fallback_output
        return create_fallback_output('architect')


class MemoryAwareTicketGeneratorAgent:
    """Ticket generator agent with memory awareness"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.memory_store = get_memory_store()
    
    def execute(self, prd: Dict[str, Any], architecture: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """Execute the ticket generator agent with memory awareness"""
        logger.info(f"🧠 EXECUTING MEMORY-AWARE TICKET GENERATOR AGENT")
        logger.info(f"   Thread ID: {thread_id}")
        
        try:
            # Get context
            context = self.memory_store.get_relevant_context(thread_id, prd.get('problem_statement', ''))
            
            # Create context-aware prompt
            prompt = self._create_context_aware_prompt(prd, architecture, context)
            
            messages = [
                SystemMessage(content="You are a ticket management expert with memory of previous conversations."),
                HumanMessage(content=prompt)
            ]
            
            start_time = time.time()
            response = self.model.generate_content(full_prompt)
            execution_time = time.time() - start_time
            
            raw_output = response.text
            logger.info(f"   Raw output generated in {execution_time:.2f}s")
            
            # Validate the output
            from schemas.agent_validation import AgentValidationFactory
            validated_output = AgentValidationFactory.validate_agent_output(
                'ticket_generator', raw_output
            )
            
            logger.info(f"   ✅ Memory-aware ticket generator completed")
            logger.info(f"   📋 Epics: {len(validated_output['epics'])}")
            
            return validated_output
            
        except Exception as e:
            logger.error(f"   ❌ Memory-aware ticket generator failed: {str(e)}")
            from schemas.agent_validation import create_fallback_output
            return create_fallback_output('ticket_generator')
    
    def _create_context_aware_prompt(self, prd: Dict[str, Any], architecture: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create context-aware prompt for ticket generator"""
        
        context_sections = []
        
        # Previous ticket structures
        if context['thread_history']:
            context_sections.append("PREVIOUS TICKET STRUCTURES:")
            for entry in context['thread_history'][-1:]:
                if 'tickets' in entry['workflow_output']:
                    tickets = entry['workflow_output']['tickets']
                    if 'epics' in tickets:
                        for epic in tickets['epics'][:1]:
                            context_sections.append(f"- Previous Epic: {epic.get('epic_name', 'N/A')}")
                            if 'stories' in epic:
                                story_count = len(epic['stories'])
                                context_sections.append(f"  Stories: {story_count}")
        
        # Similar ticket patterns
        if context['similar_ideas']:
            context_sections.append("\nSIMILAR PRODUCT TICKETS:")
            for similar in context['similar_ideas'][:1]:
                entry = similar['entry']
                if 'tickets' in entry['workflow_output']:
                    tickets = entry['workflow_output']['tickets']
                    total_tasks = sum(
                        len(story.get('tasks', [])) 
                        for epic in tickets.get('epics', []) 
                        for story in epic.get('stories', [])
                    )
                    context_sections.append(f"- Similar Tasks: {total_tasks}")
        
        context_text = "\n".join(context_sections) if context_sections else "No previous context available."
        
        problem_statement = prd.get('problem_statement', 'Problem statement')
        user_stories = prd.get('user_stories', [])
        tech_stack = architecture.get('tech_stack', {})
        api_endpoints = architecture.get('api_endpoints', [])
        
        return f"""
You are a Jira/Ticket Management specialist with access to previous conversation context. Your task is to create comprehensive development tickets based on the PRD and system architecture, leveraging insights from previous similar projects.

CONTEXT INFORMATION:
{context_text}

REQUIREMENTS:
- Problem Statement: {problem_statement}
- User Stories: {len(user_stories)} stories defined
- Tech Stack: {', '.join(tech_stack.keys())}
- API Endpoints: {len(api_endpoints)} endpoints defined

Please respond with a JSON object containing:
- epics: List of epics with epic_name, description, and stories (1-10 epics)

CONTEXT GUIDELINES:
- Consider previous successful epic structures
- Build upon proven task patterns
- Learn from previous time estimates
- Maintain consistency with established ticket organization

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.
"""
    
    def _execute_fallback(self, prd: Dict[str, Any], architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback execution without memory"""
        from schemas.agent_validation import create_fallback_output
        return create_fallback_output('ticket_generator')
