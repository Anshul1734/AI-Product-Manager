from typing import Optional, Dict, Any, List
from typing_extensions import TypedDict
from schemas.planner import ProductVision
from schemas.analyst import PRD
from schemas.architect import SystemArchitecture
from schemas.ticket_generator import Tickets

class WorkflowState(TypedDict):
    """State management for LangGraph workflow"""
    product_idea: str
    plan: Optional[ProductVision]
    prd: Optional[PRD]
    architecture: Optional[SystemArchitecture]
    tickets: Optional[Tickets]
    current_step: str
    errors: Dict[str, str]
    execution_time: Dict[str, float]
    completed_steps: List[str]
    is_complete: bool
