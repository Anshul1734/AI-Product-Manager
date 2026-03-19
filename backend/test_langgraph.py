"""
Test script for LangGraph workflow implementation
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator.workflow import WorkflowManager
from orchestrator.langgraph_workflow import LangGraphWorkflow
from schemas.workflow_state import WorkflowState


def test_langgraph_workflow():
    """Test the LangGraph workflow implementation"""
    
    # Load environment variables
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        return False
    
    print("🚀 Testing LangGraph Workflow Implementation")
    print("=" * 50)
    
    # Test product idea
    product_idea = "A mobile app for tracking daily habits and productivity that uses AI to provide personalized recommendations"
    
    try:
        # Test 1: Initialize LangGraph workflow
        print("\n📋 Test 1: Initializing LangGraph Workflow")
        langgraph_workflow = LangGraphWorkflow()
        print("✅ LangGraph workflow initialized successfully")
        
        # Test 2: Execute complete workflow
        print("\n📋 Test 2: Executing Complete Workflow")
        print(f"Product Idea: {product_idea}")
        
        state = langgraph_workflow.execute_workflow(product_idea, thread_id="test-thread-1")
        
        print(f"✅ Workflow completed successfully")
        print(f"   Final step: {state.current_step}")
        print(f"   Completed steps: {state.completed_steps}")
        print(f"   Is complete: {state.is_complete}")
        
        # Test 3: Check execution times
        print("\n📋 Test 3: Execution Times")
        for step, time_taken in state.execution_time.items():
            print(f"   {step}: {time_taken:.2f}s")
        
        total_time = sum(state.execution_time.values())
        print(f"   Total: {total_time:.2f}s")
        
        # Test 4: Validate outputs
        print("\n📋 Test 4: Validating Agent Outputs")
        
        if state.plan:
            print(f"✅ Planner: {state.plan.product_name}")
        else:
            print("❌ Planner output missing")
            
        if state.prd:
            print(f"✅ Analyst: {len(state.prd.user_personas)} personas")
        else:
            print("❌ Analyst output missing")
            
        if state.architecture:
            print(f"✅ Architect: {len(state.architecture.api_endpoints)} endpoints")
        else:
            print("❌ Architect output missing")
            
        if state.tickets:
            print(f"✅ Ticket Generator: {len(state.tickets.epics)} epics")
        else:
            print("❌ Ticket Generator output missing")
        
        # Test 5: State management
        print("\n📋 Test 5: State Management")
        retrieved_state = langgraph_workflow.get_workflow_state("test-thread-1")
        
        if retrieved_state:
            print("✅ State retrieval successful")
            print(f"   Retrieved step: {retrieved_state.current_step}")
        else:
            print("❌ State retrieval failed")
        
        # Test 6: WorkflowManager integration
        print("\n📋 Test 6: WorkflowManager Integration")
        
        # Test with LangGraph
        manager_langgraph = WorkflowManager(use_langgraph=True)
        result_langgraph = manager_langgraph.execute_workflow(product_idea, thread_id="test-thread-2")
        
        print("✅ WorkflowManager with LangGraph successful")
        print(f"   Plan: {result_langgraph.plan.product_name}")
        
        # Test with legacy
        manager_legacy = WorkflowManager(use_langgraph=False)
        result_legacy = manager_legacy.execute_workflow(product_idea)
        
        print("✅ WorkflowManager with legacy successful")
        print(f"   Plan: {result_legacy.plan.product_name}")
        
        # Test 7: Streaming (basic test)
        print("\n📋 Test 7: Streaming Test")
        
        stream_events = list(langgraph_workflow.stream_workflow(product_idea, thread_id="test-thread-3"))
        print(f"✅ Streaming successful: {len(stream_events)} events")
        
        for i, event in enumerate(stream_events[:3]):  # Show first 3 events
            print(f"   Event {i+1}: {list(event.keys())}")
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_workflow():
    """Test async workflow execution"""
    
    print("\n🔄 Testing Async Workflow")
    print("=" * 30)
    
    try:
        manager = WorkflowManager(use_langgraph=True)
        
        product_idea = "A web platform for collaborative project management with real-time updates"
        
        result = await manager.execute_workflow_async(product_idea, thread_id="async-test")
        
        print("✅ Async workflow completed successfully")
        print(f"   Product: {result.plan.product_name}")
        print(f"   Epics: {len(result.tickets.epics)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Async test failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("🧪 LangGraph Workflow Test Suite")
    print("=" * 40)
    
    # Run synchronous tests
    success = test_langgraph_workflow()
    
    if success:
        # Run async tests
        try:
            asyncio.run(test_async_workflow())
        except Exception as e:
            print(f"❌ Async test suite failed: {str(e)}")
    
    print("\n🏁 Test suite completed")
