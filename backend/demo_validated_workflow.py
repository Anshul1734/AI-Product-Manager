"""
Demonstration of the validated workflow system
"""
import json
from agents.validated_agents import ValidatedWorkflowManager
from utils.logging import logger


def demo_validated_workflow():
    """Demonstrate the validated workflow with a sample product idea"""
    
    logger.info("🚀 DEMONSTRATING VALIDATED WORKFLOW SYSTEM")
    
    # Sample product idea
    product_idea = "AI-powered project management tool for remote teams with real-time collaboration and automated task scheduling"
    
    logger.info(f"📝 Product Idea: {product_idea}")
    
    # Create validated workflow manager
    workflow_manager = ValidatedWorkflowManager()
    
    try:
        # Execute the workflow
        logger.info("🔄 EXECUTING VALIDATED WORKFLOW...")
        result = workflow_manager.execute_workflow(product_idea, "demo-thread-123")
        
        if result.get('success', True):
            logger.info("✅ WORKFLOW COMPLETED SUCCESSFULLY")
            
            # Display results summary
            logger.info("📊 RESULTS SUMMARY:")
            logger.info(f"   - Product Name: {result['plan']['product_name']}")
            logger.info(f"   - Problem Statement: {result['prd']['problem_statement'][:100]}...")
            logger.info(f"   - System Design: {result['architecture']['system_design']}")
            logger.info(f"   - Total Epics: {len(result['tickets']['epics'])}")
            logger.info(f"   - Execution Time: {result.get('execution_time', 0):.2f}s")
            
            # Show agent times
            if 'agent_times' in result:
                logger.info("⏱️  AGENT EXECUTION TIMES:")
                for agent, time_taken in result['agent_times'].items():
                    logger.info(f"   - {agent.title()}: {time_taken:.2f}s")
            
            # Validate that all outputs are properly structured
            logger.info("🔍 OUTPUT VALIDATION:")
            
            # Check planner output
            plan = result['plan']
            logger.info(f"   ✅ Planner: {plan['product_name']} ({len(plan['target_users'])} users)")
            
            # Check analyst output
            prd = result['prd']
            logger.info(f"   ✅ Analyst: {len(prd['user_personas'])} personas, {len(prd['user_stories'])} stories")
            
            # Check architect output
            arch = result['architecture']
            logger.info(f"   ✅ Architect: {len(arch['api_endpoints'])} endpoints, {len(arch['database_schema'])} tables")
            
            # Check ticket output
            tickets = result['tickets']
            total_stories = sum(len(epic['stories']) for epic in tickets['epics'])
            total_tasks = sum(len(story['tasks']) for epic in tickets['epics'] for story in epic['stories'])
            logger.info(f"   ✅ Tickets: {len(tickets['epics'])} epics, {total_stories} stories, {total_tasks} tasks")
            
        else:
            logger.error("❌ WORKFLOW FAILED")
            logger.error(f"   Error: {result.get('error', 'Unknown error')}")
            
            if 'fallback_data' in result:
                logger.info("🔄 USING FALLBACK DATA")
                fallback = result['fallback_data']
                logger.info(f"   - Fallback Product: {fallback['plan']['product_name']}")
        
    except Exception as e:
        logger.error(f"❌ DEMONSTRATION FAILED: {str(e)}")
    
    logger.info("🎉 DEMONSTRATION COMPLETED")


def demo_validation_scenarios():
    """Demonstrate various validation scenarios"""
    
    logger.info("\n🧪 DEMONSTRATING VALIDATION SCENARIOS")
    
    scenarios = [
        {
            "name": "Valid Product Idea",
            "idea": "AI-powered customer service chatbot for e-commerce websites",
            "expected": "success"
        },
        {
            "name": "Short Product Idea",
            "idea": "AI tool",
            "expected": "success_with_validation"
        },
        {
            "name": "Complex Product Idea",
            "idea": "Comprehensive enterprise resource planning system with AI-driven forecasting, blockchain-based supply chain tracking, and real-time analytics dashboard for multinational corporations",
            "expected": "success"
        }
    ]
    
    workflow_manager = ValidatedWorkflowManager()
    
    for scenario in scenarios:
        logger.info(f"\n--- SCENARIO: {scenario['name']} ---")
        logger.info(f"Idea: {scenario['idea']}")
        
        try:
            result = workflow_manager.execute_workflow(scenario['idea'])
            
            if result.get('success', True):
                logger.info("✅ Scenario completed successfully")
                logger.info(f"   Product: {result['plan']['product_name']}")
            else:
                logger.info("⚠️  Scenario completed with fallback")
                logger.info(f"   Error: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"❌ Scenario failed: {str(e)}")
    
    logger.info("\n🎉 VALIDATION SCENARIOS COMPLETED")


if __name__ == "__main__":
    demo_validated_workflow()
    demo_validation_scenarios()
