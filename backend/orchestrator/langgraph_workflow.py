import logging
import time
import uuid
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents import PlannerAgent, AnalystAgent, ArchitectAgent, TicketGeneratorAgent
from schemas.workflow_state import WorkflowState


logger = logging.getLogger(__name__)


class LangGraphWorkflow:
    """LangGraph-based workflow orchestration"""
    
    def __init__(self):
        self.planner = PlannerAgent()
        self.analyst = AnalystAgent()
        self.architect = ArchitectAgent()
        self.ticket_generator = TicketGeneratorAgent()
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        
        # Add memory for checkpointing
        self.memory = MemorySaver()
        self.app = self.workflow.compile(checkpointer=self.memory)
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow graph"""
        
        # Create the graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes for each agent
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("analyst", self._analyst_node)
        workflow.add_node("architect", self._architect_node)
        workflow.add_node("ticket_generator", self._ticket_generator_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Define the flow
        workflow.set_entry_point("planner")
        
        # Conditional edges for error handling (do NOT also add unconditional edges from same nodes)
        workflow.add_conditional_edges(
            "planner",
            self._should_continue_to_analyst,
            {
                "continue": "analyst",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "analyst",
            self._should_continue_to_architect,
            {
                "continue": "architect",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "architect",
            self._should_continue_to_tickets,
            {
                "continue": "ticket_generator",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "ticket_generator",
            self._should_end_workflow,
            {
                "end": END,
                "error": "error_handler"
            }
        )
        
        workflow.add_edge("error_handler", END)
        
        return workflow

    
    def _planner_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Planner agent node"""
        start_time = time.time()
        
        try:
            logger.info("Executing planner node")
            
            # Generate product vision
            plan = self.planner.generate_vision(state["product_idea"])
            
            execution_time = time.time() - start_time
            
            return {
                "plan": plan,
                "current_step": "planner",
                "completed_steps": state["completed_steps"] + ["planner"],
                "execution_time": {**state["execution_time"], "planner": execution_time}
            }
            
        except Exception as e:
            logger.error(f"Planner node failed: {str(e)}")
            return {
                "current_step": "planner_error",
                "errors": {**state["errors"], "planner": str(e)},
                "execution_time": {**state["execution_time"], "planner": time.time() - start_time}
            }
    
    def _analyst_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Analyst agent node"""
        start_time = time.time()
        
        try:
            logger.info("Executing analyst node")
            
            if not state["plan"]:
                raise ValueError("No product vision available for analyst")
            
            # Generate PRD
            prd = self.analyst.generate_prd(state["plan"])
            
            execution_time = time.time() - start_time
            
            return {
                "prd": prd,
                "current_step": "analyst",
                "completed_steps": state["completed_steps"] + ["analyst"],
                "execution_time": {**state["execution_time"], "analyst": execution_time}
            }
            
        except Exception as e:
            logger.error(f"Analyst node failed: {str(e)}")
            return {
                "current_step": "analyst_error",
                "errors": {**state["errors"], "analyst": str(e)},
                "execution_time": {**state["execution_time"], "analyst": time.time() - start_time}
            }
    
    def _architect_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Architect agent node"""
        start_time = time.time()
        
        try:
            logger.info("Executing architect node")
            
            if not state["prd"]:
                raise ValueError("No PRD available for architect")
            
            # Generate architecture
            architecture = self.architect.generate_architecture(state["prd"])
            
            execution_time = time.time() - start_time
            
            return {
                "architecture": architecture,
                "current_step": "architect",
                "completed_steps": state["completed_steps"] + ["architect"],
                "execution_time": {**state["execution_time"], "architect": execution_time}
            }
            
        except Exception as e:
            logger.error(f"Architect node failed: {str(e)}")
            return {
                "current_step": "architect_error",
                "errors": {**state["errors"], "architect": str(e)},
                "execution_time": {**state["execution_time"], "architect": time.time() - start_time}
            }
    
    def _ticket_generator_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Ticket generator agent node"""
        start_time = time.time()
        
        try:
            logger.info("Executing ticket generator node")
            
            if not state["prd"] or not state["architecture"]:
                raise ValueError("No PRD or architecture available for ticket generator")
            
            # Generate tickets
            tickets = self.ticket_generator.generate_tickets(state["prd"], state["architecture"])
            
            execution_time = time.time() - start_time
            
            return {
                "tickets": tickets,
                "current_step": "ticket_generator",
                "completed_steps": state["completed_steps"] + ["ticket_generator"],
                "is_complete": True,
                "execution_time": {**state["execution_time"], "ticket_generator": execution_time}
            }
            
        except Exception as e:
            logger.error(f"Ticket generator node failed: {str(e)}")
            return {
                "current_step": "ticket_generator_error",
                "errors": {**state["errors"], "ticket_generator": str(e)},
                "execution_time": {**state["execution_time"], "ticket_generator": time.time() - start_time}
            }
    
    def _error_handler_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Error handler node"""
        logger.error(f"Workflow error in step: {state['current_step']}")
        logger.error(f"Errors: {state['errors']}")
        
        return {
            "current_step": "error",
            "is_complete": True
        }
    
    def _should_continue_to_analyst(self, state: WorkflowState) -> str:
        """Check if should continue to analyst"""
        return "continue" if state["plan"] and "planner" not in state["errors"] else "error"
    
    def _should_continue_to_architect(self, state: WorkflowState) -> str:
        """Check if should continue to architect"""
        return "continue" if state["prd"] and "analyst" not in state["errors"] else "error"
    
    def _should_continue_to_tickets(self, state: WorkflowState) -> str:
        """Check if should continue to ticket generator"""
        return "continue" if state["architecture"] and "architect" not in state["errors"] else "error"
    
    def _should_end_workflow(self, state: WorkflowState) -> str:
        """Check if should end workflow"""
        return "end" if state["tickets"] and "ticket_generator" not in state["errors"] else "error"
    
    def execute_workflow(self, product_idea: str, thread_id: Optional[str] = None) -> WorkflowState:
        """
        Execute the LangGraph workflow
        
        Args:
            product_idea: The product idea to process
            thread_id: Optional thread ID for conversation memory
            
        Returns:
            WorkflowState: Final workflow state
        """
        try:
            # Initialize state
            initial_state = {
                "product_idea": product_idea,
                "plan": None,
                "prd": None,
                "architecture": None,
                "tickets": None,
                "current_step": "start",
                "errors": {},
                "execution_time": {},
                "completed_steps": [],
                "is_complete": False
            }
            
            # Configure execution
            config = {}
            if not thread_id:
                thread_id = str(uuid.uuid4())
            config["configurable"] = {"thread_id": thread_id}
            
            # Execute workflow
            logger.info(f"Starting LangGraph workflow for: {product_idea[:100]}...")
            
            result = self.app.invoke(initial_state, config=config)
            
            logger.info(f"LangGraph workflow completed. Final step: {result['current_step']}")
            
            return result
            
        except Exception as e:
            logger.error(f"LangGraph workflow execution failed: {str(e)}")
            raise
    
    async def execute_workflow_async(self, product_idea: str, thread_id: Optional[str] = None) -> WorkflowState:
        """Async version of execute_workflow"""
        return self.execute_workflow(product_idea, thread_id)
    
    def get_workflow_state(self, thread_id: str) -> Optional[WorkflowState]:
        """Get current workflow state for a thread"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.app.get_state(config)
            return state.values if state else None
        except Exception as e:
            logger.error(f"Failed to get workflow state: {str(e)}")
            return None
    
    def stream_workflow(self, product_idea: str, thread_id: Optional[str] = None):
        """Stream workflow execution step by step"""
        try:
            # Initialize state
            initial_state = {
                "product_idea": product_idea,
                "plan": None,
                "prd": None,
                "architecture": None,
                "tickets": None,
                "current_step": "start",
                "errors": {},
                "execution_time": {},
                "completed_steps": [],
                "is_complete": False
            }
            
            # Configure execution
            config = {}
            if not thread_id:
                thread_id = str(uuid.uuid4())
            config["configurable"] = {"thread_id": thread_id}
            
            # Stream workflow
            logger.info(f"Starting LangGraph workflow stream for: {product_idea[:100]}...")
            
            for event in self.app.stream(initial_state, config=config):
                yield event
                
        except Exception as e:
            logger.error(f"LangGraph workflow stream failed: {str(e)}")
            raise
