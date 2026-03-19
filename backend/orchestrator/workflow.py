import logging
from typing import Optional, Dict, Any, Iterator
from agents import PlannerAgent, AnalystAgent, ArchitectAgent, TicketGeneratorAgent
from schemas import WorkflowOutput, ProductVision, PRD, SystemArchitecture, Tickets
from schemas.workflow_state import WorkflowState
from .langgraph_workflow import LangGraphWorkflow


logger = logging.getLogger(__name__)


class WorkflowManager:
    """Orchestrates the multi-agent workflow for product management using LangGraph"""
    
    def __init__(self, use_langgraph: bool = True):
        """
        Initialize workflow manager
        
        Args:
            use_langgraph: Whether to use LangGraph (recommended) or legacy sequential execution
        """
        self.use_langgraph = use_langgraph
        
        if self.use_langgraph:
            self.langgraph_workflow = LangGraphWorkflow()
            logger.info("WorkflowManager initialized with LangGraph")
        else:
            # Legacy agents for backward compatibility
            self.planner = PlannerAgent()
            self.analyst = AnalystAgent()
            self.architect = ArchitectAgent()
            self.ticket_generator = TicketGeneratorAgent()
            logger.info("WorkflowManager initialized with legacy sequential execution")
    
    def execute_workflow(self, product_idea: str, thread_id: Optional[str] = None) -> WorkflowOutput:
        """
        Execute the complete workflow using LangGraph or legacy sequential execution
        
        Args:
            product_idea: Raw product idea description
            thread_id: Optional thread ID for conversation memory (LangGraph only)
            
        Returns:
            WorkflowOutput: Complete workflow results
            
        Raises:
            ValueError: If any agent returns invalid JSON
            RuntimeError: If any agent execution fails
        """
        if self.use_langgraph:
            return self._execute_langgraph_workflow(product_idea, thread_id)
        else:
            return self._execute_legacy_workflow(product_idea)
    
    def _execute_langgraph_workflow(self, product_idea: str, thread_id: Optional[str] = None) -> WorkflowOutput:
        """Execute workflow using LangGraph"""
        try:
            logger.info("Starting LangGraph workflow execution")
            
            # Execute LangGraph workflow
            state = self.langgraph_workflow.execute_workflow(product_idea, thread_id)
            
            # Check for errors
            if state["errors"]:
                error_messages = [f"{step}: {error}" for step, error in state["errors"].items()]
                raise RuntimeError(f"LangGraph workflow errors: {'; '.join(error_messages)}")
            
            # Validate completion
            if not state["is_complete"]:
                raise RuntimeError("LangGraph workflow did not complete successfully")
            
            # Convert to WorkflowOutput
            workflow_output = WorkflowOutput(
                plan=state["plan"],
                prd=state["prd"],
                architecture=state["architecture"],
                tickets=state["tickets"]
            )
            
            total_time = sum(state["execution_time"].values())
            logger.info(f"LangGraph workflow completed in {total_time:.2f} seconds")
            
            return workflow_output
            
        except Exception as e:
            logger.error(f"LangGraph workflow execution failed: {str(e)}")
            raise
    
    def _execute_legacy_workflow(self, product_idea: str) -> WorkflowOutput:
        """Execute workflow using legacy sequential execution"""
        try:
            logger.info("Starting legacy workflow execution")
            
            # Step 1: Planner Agent - Generate product vision
            logger.info("Step 1: Generating product vision")
            plan = self.planner.generate_vision(product_idea)
            logger.info(f"Generated product vision: {plan.product_name}")
            
            # Step 2: Analyst Agent - Generate PRD
            logger.info("Step 2: Generating PRD")
            prd = self.analyst.generate_prd(plan)
            logger.info(f"Generated PRD with {len(prd.user_personas)} personas")
            
            # Step 3: Architect Agent - Generate system architecture
            logger.info("Step 3: Generating system architecture")
            architecture = self.architect.generate_architecture(prd)
            logger.info(f"Generated architecture with {len(architecture.api_endpoints)} endpoints")
            
            # Step 4: Ticket Generator Agent - Generate tickets
            logger.info("Step 4: Generating tickets")
            tickets = self.ticket_generator.generate_tickets(prd, architecture)
            logger.info(f"Generated {len(tickets.epics)} epics")
            
            # Combine all results
            workflow_output = WorkflowOutput(
                plan=plan,
                prd=prd,
                architecture=architecture,
                tickets=tickets
            )
            
            logger.info("Legacy workflow execution completed successfully")
            return workflow_output
            
        except Exception as e:
            logger.error(f"Legacy workflow execution failed: {str(e)}")
            raise
    
    async def execute_workflow_async(self, product_idea: str, thread_id: Optional[str] = None) -> WorkflowOutput:
        """Async version of execute_workflow"""
        if self.use_langgraph:
            state = await self.langgraph_workflow.execute_workflow_async(product_idea, thread_id)
            
            if state["errors"]:
                error_messages = [f"{step}: {error}" for step, error in state["errors"].items()]
                raise RuntimeError(f"LangGraph workflow errors: {'; '.join(error_messages)}")
            
            return WorkflowOutput(
                plan=state["plan"],
                prd=state["prd"],
                architecture=state["architecture"],
                tickets=state["tickets"]
            )
        else:
            return self.execute_workflow(product_idea)
    
    def stream_workflow(self, product_idea: str, thread_id: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """
        Stream workflow execution step by step (LangGraph only)
        
        Args:
            product_idea: Raw product idea description
            thread_id: Optional thread ID for conversation memory
            
        Yields:
            Dict: Step results and metadata
        """
        if not self.use_langgraph:
            raise NotImplementedError("Streaming is only available with LangGraph")
        
        try:
            logger.info("Starting LangGraph workflow stream")
            
            for event in self.langgraph_workflow.stream_workflow(product_idea, thread_id):
                yield event
                
        except Exception as e:
            logger.error(f"LangGraph workflow stream failed: {str(e)}")
            raise
    
    def get_workflow_state(self, thread_id: str) -> Optional[WorkflowState]:
        """
        Get current workflow state for a thread (LangGraph only)
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            WorkflowState: Current workflow state or None
        """
        if not self.use_langgraph:
            raise NotImplementedError("State management is only available with LangGraph")
        
        return self.langgraph_workflow.get_workflow_state(thread_id)
    
    def execute_step(self, product_idea: str, step: str) -> dict:
        """
        Execute a single step of the workflow (legacy mode only)
        
        Args:
            product_idea: Raw product idea description
            step: One of "planner", "analyst", "architect", "ticket_generator"
            
        Returns:
            dict: Result of the specific step
        """
        if self.use_langgraph:
            raise NotImplementedError("Step execution is only available in legacy mode")
        
        try:
            if step == "planner":
                return self.planner.generate_vision(product_idea).model_dump()
            else:
                # For other steps, we need the previous step's output
                # This is a simplified version - in practice you'd pass the required input
                raise ValueError(f"Step '{step}' requires previous step output")
        except Exception as e:
            logger.error(f"Step '{step}' execution failed: {str(e)}")
            raise
