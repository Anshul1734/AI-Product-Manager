"""
Test script to demonstrate the intelligent workflow with evaluator agent
"""
import json
from agents.intelligent_workflow_manager import create_intelligent_workflow_manager
from utils.logging import logger


def test_intelligent_workflow():
    """Test the intelligent workflow with evaluation enabled"""
    
    logger.info("🧪 TESTING INTELLIGENT WORKFLOW WITH EVALUATION")
    
    # Create intelligent workflow manager
    workflow_manager = create_intelligent_workflow_manager(
        model_name="gpt-3.5-turbo",
        evaluator_model="gpt-4"
    )
    
    # Sample product idea
    product_idea = "AI-powered project management tool for remote teams with real-time collaboration and automated task scheduling"
    
    logger.info(f"📝 Product Idea: {product_idea}")
    
    try:
        # Execute workflow with evaluation enabled
        logger.info("🔄 EXECUTING WORKFLOW WITH EVALUATION...")
        result = workflow_manager.execute_workflow(
            product_idea, 
            thread_id="test-intelligent-001",
            enable_evaluation=True
        )
        
        if result.get('success', True):
            logger.info("✅ INTELLIGENT WORKFLOW COMPLETED SUCCESSFULLY")
            
            # Display results
            logger.info("📊 RESULTS SUMMARY:")
            logger.info(f"   - Product Name: {result['plan']['product_name']}")
            logger.info(f"   - Execution Time: {result.get('execution_time', 0):.2f}s")
            logger.info(f"   - Evaluation Enabled: {result.get('evaluation_enabled', False)}")
            logger.info(f"   - Improvements Made: {result.get('improvements_made', False)}")
            
            # Show quality report if available
            if 'evaluation' in result:
                quality_report = workflow_manager.get_quality_report(result)
                logger.info(f"📈 QUALITY GRADE: {quality_report['quality_grade']}")
                logger.info(f"   Overall Score: {quality_report['overall_quality']:.1f}/10")
                
                # Show detailed scores
                detailed_scores = quality_report['detailed_scores']
                logger.info("📋 DETAILED SCORES:")
                for criterion, score in detailed_scores.items():
                    logger.info(f"   - {criterion.title()}: {score:.1f}/10")
                
                # Show critical issues if any
                if quality_report['critical_issues']:
                    logger.warning("⚠️  CRITICAL ISSUES:")
                    for issue in quality_report['critical_issues']:
                        logger.warning(f"   - {issue}")
                
                # Show improvement recommendations
                if quality_report['improvement_recommendations']:
                    logger.info("💡 IMPROVEMENT RECOMMENDATIONS:")
                    for rec in quality_report['improvement_recommendations']:
                        logger.info(f"   - {rec}")
            
            # Show agent execution times
            logger.info("⏱️  AGENT EXECUTION TIMES:")
            for agent, time_taken in result.get('agent_times', {}).items():
                logger.info(f"   - {agent.title()}: {time_taken:.2f}s")
            
        else:
            logger.error("❌ INTELLIGENT WORKFLOW FAILED")
            logger.error(f"   Error: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")
    
    logger.info("🎉 INTELLIGENT WORKFLOW TEST COMPLETED")


def test_workflow_comparison():
    """Test workflow comparison functionality"""
    
    logger.info("\n🧪 TESTING WORKFLOW COMPARISON")
    
    workflow_manager = create_intelligent_workflow_manager()
    
    # Sample outputs for comparison
    workflow1 = {
        'evaluation_result': {
            'quality_metrics': {'overall_quality': 7.5}
        },
        'execution_time': 10.5,
        'improvements_made': False,
        'plan': {}, 'prd': {}, 'architecture': {}, 'tickets': {}
    }
    
    workflow2 = {
        'evaluation_result': {
            'quality_metrics': {'overall_quality': 8.2}
        },
        'execution_time': 12.3,
        'improvements_made': True,
        'plan': {}, 'prd': {}, 'architecture': {}, 'tickets': {}
    }
    
    try:
        comparison = workflow_manager.compare_workflows(workflow1, workflow2)
        
        logger.info("📊 COMPARISON RESULTS:")
        logger.info(f"   - Workflow 1 Quality: {comparison['workflow1_quality']:.1f}")
        logger.info(f"   - Workflow 2 Quality: {comparison['workflow2_quality']:.1f}")
        logger.info(f"   - Quality Difference: {comparison['quality_difference']:+.2f}")
        logger.info(f"   - Better Workflow: {comparison['better_workflow']}")
        
    except Exception as e:
        logger.error(f"❌ COMPARISON TEST FAILED: {str(e)}")
    
    logger.info("🎉 WORKFLOW COMPARISON TEST COMPLETED")


def test_quality_grading():
    """Test quality grading system"""
    
    logger.info("\n🧪 TESTING QUALITY GRADING")
    
    workflow_manager = create_intelligent_workflow_manager()
    
    test_scores = [9.5, 8.7, 7.3, 6.5, 5.2, 3.8]
    
    for score in test_scores:
        grade = workflow_manager._get_quality_grade(score)
        logger.info(f"   Score {score:.1f} → Grade: {grade}")
    
    logger.info("🎉 QUALITY GRADING TEST COMPLETED")


def test_evaluation_scenarios():
    """Test different evaluation scenarios"""
    
    logger.info("\n🧪 TESTING EVALUATION SCENARIOS")
    
    workflow_manager = create_intelligent_workflow_manager()
    
    scenarios = [
        {
            "name": "High Quality Output",
            "idea": "Simple mobile app for personal task management",
            "expected_quality": "Good"
        },
        {
            "name": "Complex Output",
            "idea": "Enterprise-scale AI-powered supply chain management system with blockchain integration and real-time analytics",
            "expected_quality": "Fair"
        },
        {
            "name": "Minimal Output",
            "idea": "Tool",
            "expected_quality": "Poor"
        }
    ]
    
    for scenario in scenarios:
        logger.info(f"\n--- SCENARIO: {scenario['name']} ---")
        logger.info(f"Idea: {scenario['idea']}")
        
        try:
            # For demonstration, we'll just run a quick test without actual LLM calls
            # In a real scenario, this would execute the full workflow
            logger.info(f"Expected Quality: {scenario['expected_quality']}")
            logger.info("✅ Scenario test completed")
            
        except Exception as e:
            logger.error(f"❌ Scenario test failed: {str(e)}")
    
    logger.info("\n🎉 EVALUATION SCENARIOS TEST COMPLETED")


if __name__ == "__main__":
    test_intelligent_workflow()
    test_workflow_comparison()
    test_quality_grading()
    test_evaluation_scenarios()
