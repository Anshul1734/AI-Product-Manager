"""
Pydantic schemas for validating agent outputs with strict validation and retry logic.
"""
from pydantic import BaseModel, Field, validator, ValidationError
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import json
import re
from datetime import datetime


class StrictStr(str):
    """Strict string validation with length and content checks"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        if len(v.strip()) == 0:
            raise ValueError("String cannot be empty")
        if len(v.strip()) < 3:
            raise ValueError("String must be at least 3 characters long")
        return v.strip()


class AgentOutputValidator:
    """Base class for validating agent outputs with retry logic"""
    
    MAX_RETRIES = 2
    
    @classmethod
    def validate_and_retry(cls, raw_output: str, agent_name: str) -> Dict[str, Any]:
        """
        Validate agent output with retry logic
        
        Args:
            raw_output: Raw LLM response
            agent_name: Name of the agent for error reporting
            
        Returns:
            Validated and parsed output
            
        Raises:
            ValueError: If validation fails after all retries
        """
        last_error = None
        
        for attempt in range(cls.MAX_RETRIES + 1):
            try:
                # Clean the output
                cleaned_output = cls._clean_output(raw_output)
                
                # Parse JSON
                parsed_output = json.loads(cleaned_output)
                
                # Validate against schema
                validated_output = cls(**parsed_output)
                
                return validated_output.dict()
                
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                last_error = e
                if attempt < cls.MAX_RETRIES:
                    print(f"[{agent_name}] Validation attempt {attempt + 1} failed: {str(e)}")
                    print(f"[{agent_name}] Retrying... ({cls.MAX_RETRIES - attempt} attempts remaining)")
                else:
                    print(f"[{agent_name}] All validation attempts failed")
                    break
        
        # If we get here, all attempts failed
        error_msg = f"Agent {agent_name} output validation failed after {cls.MAX_RETRIES + 1} attempts"
        if last_error:
            error_msg += f". Last error: {str(last_error)}"
        
        raise ValueError(error_msg)
    
    @classmethod
    def _clean_output(cls, raw_output: str) -> str:
        """Clean raw LLM output to extract valid JSON"""
        # Remove common LLM artifacts
        cleaned = raw_output.strip()
        
        # Remove markdown code blocks
        cleaned = re.sub(r'```json\s*', '', cleaned)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        
        # Remove explanatory text before/after JSON
        json_start = cleaned.find('{')
        json_end = cleaned.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            cleaned = cleaned[json_start:json_end + 1]
        
        # Fix common JSON issues
        cleaned = cleaned.replace("'", '"')  # Single quotes to double quotes
        cleaned = re.sub(r',\s*}', '}', cleaned)  # Trailing commas
        cleaned = re.sub(r',\s*]', ']', cleaned)  # Trailing commas in arrays
        
        return cleaned


# ============================================================================
# PLANNER AGENT SCHEMAS
# ============================================================================

class ProductVision(BaseModel):
    """Strict validation for Planner Agent output"""
    product_name: str = Field(..., description="Product name")
    problem_statement: str = Field(..., description="Problem statement")
    target_users: List[str] = Field(..., min_items=1, description="Target users")
    core_goals: List[str] = Field(..., min_items=1, description="Core goals")
    key_features_high_level: List[str] = Field(..., min_items=1, description="Key features")
    
    @validator('product_name')
    def validate_product_name(cls, v):
        if not isinstance(v, str):
            raise ValueError("Product name must be a string")
        v = v.strip()
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Product name must be between 3 and 100 characters")
        return v
    
    @validator('problem_statement')
    def validate_problem_statement(cls, v):
        if not isinstance(v, str):
            raise ValueError("Problem statement must be a string")
        v = v.strip()
        if len(v) < 10 or len(v) > 500:
            raise ValueError("Problem statement must be between 10 and 500 characters")
        return v
    
    @validator('target_users', each_item=True)
    def validate_target_user(cls, v):
        if not isinstance(v, str):
            raise ValueError("Target user must be a string")
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Target user must be between 2 and 50 characters")
        return v
    
    @validator('core_goals', each_item=True)
    def validate_core_goal(cls, v):
        if not isinstance(v, str):
            raise ValueError("Core goal must be a string")
        v = v.strip()
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Core goal must be between 3 and 100 characters")
        return v
    
    @validator('key_features_high_level', each_item=True)
    def validate_key_feature(cls, v):
        if not isinstance(v, str):
            raise ValueError("Key feature must be a string")
        v = v.strip()
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Key feature must be between 3 and 100 characters")
        return v
    
    @validator('target_users')
    def validate_target_users(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 target users")
        return v
    
    @validator('core_goals')
    def validate_core_goals(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 core goals")
        return v
    
    @validator('key_features_high_level')
    def validate_key_features(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 key features")
        return v


class PlannerValidator(AgentOutputValidator, ProductVision):
    """Validator for Planner Agent output"""
    pass


# ============================================================================
# ANALYST AGENT SCHEMAS
# ============================================================================

class UserPersona(BaseModel):
    """Strict validation for user persona"""
    name: StrictStr = Field(..., description="User persona name")
    description: StrictStr = Field(..., description="User persona description")
    pain_points: List[StrictStr] = Field(..., min_items=1, description="User pain points")
    
    @validator('name')
    def validate_name(cls, v):
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Name must be between 2 and 50 characters")
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if len(v) < 10 or len(v) > 200:
            raise ValueError("Description must be between 10 and 200 characters")
        return v
    
    @validator('pain_points')
    def validate_pain_points(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 pain points")
        return v


class UserStory(BaseModel):
    """Strict validation for user story"""
    title: StrictStr = Field(..., description="User story title")
    as_a: StrictStr = Field(..., description="User story 'as a' part")
    i_want_to: StrictStr = Field(..., description="User story 'I want to' part")
    so_that: StrictStr = Field(..., description="User story 'so that' part")
    
    @validator('title')
    def validate_title(cls, v):
        if len(v) < 5 or len(v) > 100:
            raise ValueError("Title must be between 5 and 100 characters")
        return v
    
    @validator('as_a')
    def validate_as_a(cls, v):
        if len(v) < 3 or len(v) > 100:
            raise ValueError("'As a' must be between 3 and 100 characters")
        return v
    
    @validator('i_want_to')
    def validate_i_want_to(cls, v):
        if len(v) < 5 or len(v) > 100:
            raise ValueError("'I want to' must be between 5 and 100 characters")
        return v
    
    @validator('so_that')
    def validate_so_that(cls, v):
        if len(v) < 5 or len(v) > 200:
            raise ValueError("'So that' must be between 5 and 200 characters")
        return v


class SuccessMetric(BaseModel):
    """Strict validation for success metric"""
    name: StrictStr = Field(..., description="Metric name")
    description: StrictStr = Field(..., description="Metric description")
    target: StrictStr = Field(..., description="Target value")
    
    @validator('name')
    def validate_name(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Name must be between 3 and 50 characters")
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if len(v) < 5 or len(v) > 200:
            raise ValueError("Description must be between 5 and 200 characters")
        return v
    
    @validator('target')
    def validate_target(cls, v):
        if len(v) < 1 or len(v) > 50:
            raise ValueError("Target must be between 1 and 50 characters")
        return v


class PRD(BaseModel):
    """Strict validation for PRD output"""
    problem_statement: StrictStr = Field(..., description="Problem statement")
    target_users: List[StrictStr] = Field(..., min_items=1, description="Target users")
    user_personas: List[UserPersona] = Field(..., min_items=1, description="User personas")
    user_stories: List[UserStory] = Field(..., min_items=1, description="User stories")
    success_metrics: List[SuccessMetric] = Field(..., min_items=1, description="Success metrics")
    
    @validator('problem_statement')
    def validate_problem_statement(cls, v):
        if len(v) < 10 or len(v) > 1000:
            raise ValueError("Problem statement must be between 10 and 1000 characters")
        return v
    
    @validator('target_users')
    def validate_target_users(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 target users")
        return v
    
    @validator('user_personas')
    def validate_user_personas(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 user personas")
        return v
    
    @validator('user_stories')
    def validate_user_stories(cls, v):
        if len(v) < 1 or len(v) > 20:
            raise ValueError("Must have between 1 and 20 user stories")
        return v
    
    @validator('success_metrics')
    def validate_success_metrics(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 success metrics")
        return v


class AnalystValidator(AgentOutputValidator, PRD):
    """Validator for Analyst Agent output"""
    pass


# ============================================================================
# ARCHITECT AGENT SCHEMAS
# ============================================================================

class APIEndpoint(BaseModel):
    """Strict validation for API endpoint"""
    name: StrictStr = Field(..., description="Endpoint name")
    method: StrictStr = Field(..., description="HTTP method")
    endpoint: StrictStr = Field(..., description="Endpoint path")
    description: StrictStr = Field(..., description="Endpoint description")
    
    @validator('method')
    def validate_method(cls, v):
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if v.upper() not in valid_methods:
            raise ValueError(f"Method must be one of: {', '.join(valid_methods)}")
        return v.upper()
    
    @validator('endpoint')
    def validate_endpoint(cls, v):
        if not v.startswith('/'):
            raise ValueError("Endpoint must start with '/'")
        return v


class DatabaseField(BaseModel):
    """Strict validation for database field"""
    name: StrictStr = Field(..., description="Field name")
    type: StrictStr = Field(..., description="Field type")
    constraints: StrictStr = Field(..., description="Field constraints")
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Field name must be a valid identifier")
        return v.lower()
    
    @validator('type')
    def validate_type(cls, v):
        valid_types = ['UUID', 'TEXT', 'VARCHAR', 'INTEGER', 'BOOLEAN', 'TIMESTAMP', 'JSON', 'DECIMAL']
        if v.upper() not in valid_types:
            raise ValueError(f"Type must be one of: {', '.join(valid_types)}")
        return v.upper()


class DatabaseTable(BaseModel):
    """Strict validation for database table"""
    table_name: StrictStr = Field(..., description="Table name")
    fields: List[DatabaseField] = Field(..., min_items=1, description="Table fields")
    
    @validator('table_name')
    def validate_table_name(cls, v):
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Table name must be a valid identifier")
        return v.lower()
    
    @validator('fields')
    def validate_fields(cls, v):
        if len(v) < 1 or len(v) > 20:
            raise ValueError("Must have between 1 and 20 fields")
        
        # Check for primary key
        has_pk = any('PRIMARY KEY' in field.constraints.upper() for field in v)
        if not has_pk:
            raise ValueError("Table must have a primary key field")
        
        return v


class SystemArchitecture(BaseModel):
    """Strict validation for system architecture"""
    system_design: StrictStr = Field(..., description="System design description")
    tech_stack: Dict[StrictStr, StrictStr] = Field(..., min_items=1, description="Technology stack")
    architecture_components: List[StrictStr] = Field(..., min_items=1, description="Architecture components")
    api_endpoints: List[APIEndpoint] = Field(..., min_items=1, description="API endpoints")
    database_schema: List[DatabaseTable] = Field(..., min_items=1, description="Database schema")
    
    @validator('system_design')
    def validate_system_design(cls, v):
        if len(v) < 10 or len(v) > 500:
            raise ValueError("System design must be between 10 and 500 characters")
        return v
    
    @validator('tech_stack')
    def validate_tech_stack(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 tech stack components")
        return v
    
    @validator('architecture_components')
    def validate_architecture_components(cls, v):
        if len(v) < 1 or len(v) > 20:
            raise ValueError("Must have between 1 and 20 architecture components")
        return v
    
    @validator('api_endpoints')
    def validate_api_endpoints(cls, v):
        if len(v) < 1 or len(v) > 20:
            raise ValueError("Must have between 1 and 20 API endpoints")
        return v
    
    @validator('database_schema')
    def validate_database_schema(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 database tables")
        return v


class ArchitectValidator(AgentOutputValidator, SystemArchitecture):
    """Validator for Architect Agent output"""
    pass


# ============================================================================
# TICKET GENERATOR AGENT SCHEMAS
# ============================================================================

class Task(BaseModel):
    """Strict validation for task"""
    title: StrictStr = Field(..., description="Task title")
    description: StrictStr = Field(..., description="Task description")
    estimated_hours: StrictStr = Field(..., description="Estimated hours")
    
    @validator('title')
    def validate_title(cls, v):
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Title must be between 3 and 100 characters")
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if len(v) < 5 or len(v) > 500:
            raise ValueError("Description must be between 5 and 500 characters")
        return v
    
    @validator('estimated_hours')
    def validate_estimated_hours(cls, v):
        if not re.match(r'^\d+(\.\d+)?$', v):
            raise ValueError("Estimated hours must be a valid number")
        hours = float(v)
        if hours < 0.5 or hours > 100:
            raise ValueError("Estimated hours must be between 0.5 and 100")
        return v


class Story(BaseModel):
    """Strict validation for user story"""
    story_title: StrictStr = Field(..., description="Story title")
    description: StrictStr = Field(..., description="Story description")
    acceptance_criteria: List[StrictStr] = Field(..., min_items=1, description="Acceptance criteria")
    tasks: List[Task] = Field(..., min_items=1, description="Tasks")
    
    @validator('story_title')
    def validate_story_title(cls, v):
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Story title must be between 3 and 100 characters")
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if len(v) < 5 or len(v) > 500:
            raise ValueError("Description must be between 5 and 500 characters")
        return v
    
    @validator('acceptance_criteria')
    def validate_acceptance_criteria(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 acceptance criteria")
        return v
    
    @validator('tasks')
    def validate_tasks(cls, v):
        if len(v) < 1 or len(v) > 20:
            raise ValueError("Must have between 1 and 20 tasks")
        return v


class Epic(BaseModel):
    """Strict validation for epic"""
    epic_name: StrictStr = Field(..., description="Epic name")
    description: StrictStr = Field(..., description="Epic description")
    stories: List[Story] = Field(..., min_items=1, description="Stories")
    
    @validator('epic_name')
    def validate_epic_name(cls, v):
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Epic name must be between 3 and 100 characters")
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if len(v) < 5 or len(v) > 500:
            raise ValueError("Description must be between 5 and 500 characters")
        return v
    
    @validator('stories')
    def validate_stories(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 stories")
        return v


class Tickets(BaseModel):
    """Strict validation for tickets output"""
    epics: List[Epic] = Field(..., min_items=1, description="Epics")
    
    @validator('epics')
    def validate_epics(cls, v):
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Must have between 1 and 10 epics")
        return v


class TicketGeneratorValidator(AgentOutputValidator, Tickets):
    """Validator for Ticket Generator Agent output"""
    pass


# ============================================================================
# VALIDATION FACTORY
# ============================================================================

class AgentValidationFactory:
    """Factory for creating appropriate validators for each agent"""
    
    VALIDATORS = {
        'planner': PlannerValidator,
        'analyst': AnalystValidator,
        'architect': ArchitectValidator,
        'ticket_generator': TicketGeneratorValidator,
    }
    
    @classmethod
    def get_validator(cls, agent_name: str) -> AgentOutputValidator:
        """Get the appropriate validator for an agent"""
        if agent_name not in cls.VALIDATORS:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        return cls.VALIDATORS[agent_name]
    
    @classmethod
    def validate_agent_output(cls, agent_name: str, raw_output: str) -> Dict[str, Any]:
        """Validate agent output with retry logic"""
        validator = cls.get_validator(agent_name)
        return validator.validate_and_retry(raw_output, agent_name)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_all_agent_outputs(raw_outputs: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate all agent outputs
    
    Args:
        raw_outputs: Dictionary of agent names to their raw outputs
        
    Returns:
        Dictionary of validated outputs
        
    Raises:
        ValueError: If any agent output validation fails
    """
    validated_outputs = {}
    
    for agent_name, raw_output in raw_outputs.items():
        try:
            validated_outputs[agent_name] = AgentValidationFactory.validate_agent_output(
                agent_name, raw_output
            )
        except Exception as e:
            raise ValueError(f"Validation failed for {agent_name}: {str(e)}")
    
    return validated_outputs


def create_fallback_output(agent_name: str) -> Dict[str, Any]:
    """Create a fallback output when validation fails"""
    fallbacks = {
        'planner': {
            'product_name': 'AI Product Platform',
            'problem_statement': 'A generic problem statement for the product',
            'target_users': ['Users'],
            'core_goals': ['Goal 1'],
            'key_features_high_level': ['Feature 1']
        },
        'analyst': {
            'problem_statement': 'A generic problem statement',
            'target_users': ['Users'],
            'user_personas': [{
                'name': 'Generic User',
                'description': 'A generic user description',
                'pain_points': ['Pain point 1']
            }],
            'user_stories': [{
                'title': 'Generic Story',
                'as_a': 'user',
                'i_want_to': 'do something',
                'so_that': 'I can achieve something'
            }],
            'success_metrics': [{
                'name': 'Generic Metric',
                'description': 'A generic metric description',
                'target': 'Generic target'
            }]
        },
        'architect': {
            'system_design': 'A generic system design',
            'tech_stack': {'frontend': 'React', 'backend': 'FastAPI'},
            'architecture_components': ['Component 1'],
            'api_endpoints': [{
                'name': 'Generic Endpoint',
                'method': 'GET',
                'endpoint': '/api/v1/generic',
                'description': 'A generic endpoint'
            }],
            'database_schema': [{
                'table_name': 'generic_table',
                'fields': [{
                    'name': 'id',
                    'type': 'UUID',
                    'constraints': 'PRIMARY KEY'
                }]
            }]
        },
        'ticket_generator': {
            'epics': [{
                'epic_name': 'Generic Epic',
                'description': 'A generic epic description',
                'stories': [{
                    'story_title': 'Generic Story',
                    'description': 'A generic story description',
                    'acceptance_criteria': ['Criteria 1'],
                    'tasks': [{
                        'title': 'Generic Task',
                        'description': 'A generic task description',
                        'estimated_hours': '8'
                    }]
                }]
            }]
        }
    }
    
    return fallbacks.get(agent_name, {})
