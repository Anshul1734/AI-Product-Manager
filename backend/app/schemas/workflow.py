"""
Workflow data schemas for the AI Product Manager application.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ProductVision(BaseModel):
    """Product vision schema."""
    
    product_name: str = Field(..., description="Product name")
    problem_statement: str = Field(..., description="Problem statement")
    target_users: List[str] = Field(..., description="Target user groups")
    core_goals: List[str] = Field(..., description="Core product goals")
    key_features_high_level: List[str] = Field(..., description="High-level features")
    value_proposition: Optional[str] = Field(None, description="Value proposition")
    market_opportunity: Optional[str] = Field(None, description="Market opportunity")


class UserPersona(BaseModel):
    """User persona schema."""
    
    name: str = Field(..., description="Persona name")
    description: str = Field(..., description="Persona description")
    pain_points: List[str] = Field(..., description="User pain points")
    goals: List[str] = Field(..., description="User goals")
    needs: List[str] = Field(..., description="User needs")
    demographics: Optional[Dict[str, Any]] = Field(None, description="Demographic information")


class UserStory(BaseModel):
    """User story schema."""
    
    title: str = Field(..., description="Story title")
    as_a: str = Field(..., description="User role")
    i_want_to: str = Field(..., description="User goal")
    so_that: str = Field(..., description="User benefit")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria")
    priority: Optional[str] = Field(None, description="Story priority")
    story_points: Optional[int] = Field(None, description="Story points estimate")


class SuccessMetric(BaseModel):
    """Success metric schema."""
    
    name: str = Field(..., description="Metric name")
    description: str = Field(..., description="Metric description")
    target: str = Field(..., description="Target value")
    measurement_method: Optional[str] = Field(None, description="How to measure")
    timeframe: Optional[str] = Field(None, description="Timeframe for achievement")


class ProductRequirements(BaseModel):
    """Product requirements document schema."""
    
    problem_statement: str = Field(..., description="Problem statement")
    user_personas: List[UserPersona] = Field(..., description="User personas")
    user_stories: List[UserStory] = Field(..., description="User stories")
    success_metrics: List[SuccessMetric] = Field(..., description="Success metrics")
    functional_requirements: List[str] = Field(default_factory=list, description="Functional requirements")
    non_functional_requirements: List[str] = Field(default_factory=list, description="Non-functional requirements")


class TechStack(BaseModel):
    """Technology stack schema."""
    
    frontend: List[str] = Field(default_factory=list, description="Frontend technologies")
    backend: List[str] = Field(default_factory=list, description="Backend technologies")
    database: List[str] = Field(default_factory=list, description="Database technologies")
    infrastructure: List[str] = Field(default_factory=list, description="Infrastructure technologies")
    third_party: List[str] = Field(default_factory=list, description="Third-party services")


class APIEndpoint(BaseModel):
    """API endpoint schema."""
    
    path: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    description: str = Field(..., description="Endpoint description")
    authentication: bool = Field(default=False, description="Requires authentication")
    rate_limit: Optional[str] = Field(None, description="Rate limiting")


class DatabaseField(BaseModel):
    """Database field schema."""
    
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type")
    constraints: str = Field(..., description="Field constraints")
    description: Optional[str] = Field(None, description="Field description")


class DatabaseTable(BaseModel):
    """Database table schema."""
    
    table_name: str = Field(..., description="Table name")
    description: Optional[str] = Field(None, description="Table description")
    fields: List[DatabaseField] = Field(..., description="Table fields")
    indexes: Optional[List[str]] = Field(default_factory=list, description="Table indexes")


class SystemArchitecture(BaseModel):
    """System architecture schema."""
    
    system_design: str = Field(..., description="High-level system design")
    tech_stack: TechStack = Field(..., description="Technology stack")
    architecture_components: List[str] = Field(..., description="Architecture components")
    api_endpoints: List[APIEndpoint] = Field(..., description="API endpoints")
    database_schema: List[DatabaseTable] = Field(..., description="Database schema")
    deployment_architecture: Optional[str] = Field(None, description="Deployment architecture")
    security_considerations: List[str] = Field(default_factory=list, description="Security considerations")


class Task(BaseModel):
    """Development task schema."""
    
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours")
    assignee: Optional[str] = Field(None, description="Task assignee")
    status: str = Field(default="To Do", description="Task status")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")


class DevelopmentStory(BaseModel):
    """Development story schema."""
    
    story_title: str = Field(..., description="Story title")
    description: str = Field(..., description="Story description")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria")
    tasks: List[Task] = Field(..., description="Development tasks")
    priority: Optional[str] = Field(None, description="Story priority")
    story_points: Optional[int] = Field(None, description="Story points")


class DevelopmentEpic(BaseModel):
    """Development epic schema."""
    
    epic_name: str = Field(..., description="Epic name")
    description: str = Field(..., description="Epic description")
    stories: List[DevelopmentStory] = Field(..., description="Epic stories")
    priority: Optional[str] = Field(None, description="Epic priority")
    estimated_duration: Optional[str] = Field(None, description="Estimated duration")


class DevelopmentTickets(BaseModel):
    """Development tickets schema."""
    
    epics: List[DevelopmentEpic] = Field(..., description="Development epics")
    total_stories: int = Field(..., description="Total number of stories")
    total_tasks: int = Field(..., description="Total number of tasks")
    estimated_total_hours: Optional[float] = Field(None, description="Estimated total hours")


class WorkflowState(BaseModel):
    """Complete workflow state schema."""
    
    plan: ProductVision = Field(..., description="Product vision")
    prd: ProductRequirements = Field(..., description="Product requirements")
    architecture: SystemArchitecture = Field(..., description="System architecture")
    tickets: DevelopmentTickets = Field(..., description="Development tickets")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Workflow metadata")
    quality_metrics: Optional[Dict[str, Any]] = Field(None, description="Quality metrics")
    execution_summary: Optional[Dict[str, Any]] = Field(None, description="Execution summary")
