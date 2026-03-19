"""
Intelligent Workflow Manager with Evaluator Agent for iterative improvement.
"""
from typing import Dict, Any, Optional
import time
from .validated_agents import (
    ValidatedPlannerAgent,
    ValidatedAnalystAgent,
    ValidatedArchitectAgent,
    ValidatedTicketGeneratorAgent
)
from .evaluator_agent import EvaluatorAgent
from utils.logging import logger


class IntelligentWorkflowManager:
    """Workflow manager with evaluator for intelligent iterative improvement"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", evaluator_model: str = "gpt-4"):
        self.planner = ValidatedPlannerAgent(model_name)
        self.analyst = ValidatedAnalystAgent(model_name)
        self.architect = ValidatedArchitectAgent(model_name)
        self.ticket_generator = ValidatedTicketGeneratorAgent(model_name)
        self.evaluator = EvaluatorAgent(evaluator_model)
        
    def execute_workflow(self, product_idea: str, thread_id: Optional[str] = None, 
                         enable_evaluation: bool = True) -> Dict[str, Any]:
        """Execute the complete intelligent workflow with evaluation and improvement"""
        logger.info(f"🧠 STARTING INTELLIGENT WORKFLOW EXECUTION")
        logger.info(f"   Product Idea: {product_idea[:100]}...")
        logger.info(f"   Thread ID: {thread_id}")
        logger.info(f"   Evaluation Enabled: {enable_evaluation}")
        
        start_time = time.time()
        agent_times = {}
        
        try:
            # Step 1: Execute initial workflow
            logger.info("📋 PHASE 1: INITIAL WORKFLOW EXECUTION")
            initial_output = self._execute_initial_workflow(product_idea, agent_times)
            
            # Step 2: Evaluate and improve if enabled
            if enable_evaluation:
                logger.info("📋 PHASE 2: EVALUATION AND IMPROVEMENT")
                final_output = self._evaluate_and_improve(initial_output, agent_times)
            else:
                logger.info("📋 PHASE 2: SKIPPED (evaluation disabled)")
                final_output = initial_output
            
            # Step 3: Prepare final result
            total_time = time.time() - start_time
            
            workflow_result = {
                'plan': final_output['plan'],
                'prd': final_output['prd'],
                'architecture': final_output['architecture'],
                'tickets': final_output['tickets'],
                'execution_time': total_time,
                'agent_times': agent_times,
                'thread_id': thread_id or f"thread_{int(time.time())}",
                'evaluation_enabled': enable_evaluation
            }
            
            # Add evaluation results if available
            if enable_evaluation and 'evaluation_result' in final_output:
                workflow_result['evaluation'] = final_output['evaluation_result']
                workflow_result['improvements_made'] = final_output.get('improvements_made', False)
            
            logger.info(f"✅ INTELLIGENT WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info(f"📊 EXECUTION SUMMARY:")
            logger.info(f"   - Total Time: {total_time:.2f}s")
            logger.info(f"   - Evaluation: {'Enabled' if enable_evaluation else 'Disabled'}")
            for agent, time_taken in agent_times.items():
                if not agent.startswith('evaluator_'):
                    logger.info(f"   - {agent.title()}: {time_taken:.2f}s")
            
            return workflow_result
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ INTELLIGENT WORKFLOW FAILED")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Execution Time: {total_time:.2f}s")
            
            # Return error response with fallback data
            from schemas.agent_validation import create_fallback_output
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': total_time,
                'thread_id': thread_id,
                'evaluation_enabled': enable_evaluation,
                'fallback_data': {
                    'plan': create_fallback_output('planner'),
                    'prd': create_fallback_output('analyst'),
                    'architecture': create_fallback_output('architect'),
                    'tickets': create_fallback_output('ticket_generator')
                }
            }
    
    def _execute_initial_workflow(self, product_idea: str, agent_times: Dict[str, float]) -> Dict[str, Any]:
        """Execute the initial workflow without evaluation"""
        
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
        
        return {
            'plan': plan,
            'prd': prd,
            'architecture': architecture,
            'tickets': tickets
        }
    
    def _evaluate_and_improve(self, workflow_output: Dict[str, Any], agent_times: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate and improve the workflow output"""
        
        # Execute evaluator
        step_start = time.time()
        evaluator_output = self.evaluator.execute(workflow_output)
        agent_times['evaluator'] = time.time() - step_start
        
        # Store evaluation result
        workflow_output['evaluation_result'] = evaluator_output.evaluation.dict()
        
        # Check if improvements were made
        if evaluator_output.improved_output:
            logger.info("🔄 IMPROVEMENTS DETECTED")
            
            # Add evaluator regeneration time
            if 'evaluator_regeneration' not in agent_times:
                agent_times['evaluator_regeneration'] = 0.0
            agent_times['evaluator_regeneration'] += evaluator_output.total_processing_time
            
            # Update workflow output with improved version
            improved_output = evaluator_output.improved_output.improved_output
            workflow_output.update(improved_output)
            workflow_output['improvements_made'] = True
            
            # Log improvement summary
            comparison = evaluator_output.improved_output.evaluation_comparison
            overall_improvement = comparison.get('overall', {}).get('improvement', 0.0)
            logger.info(f"📈 QUALITY IMPROVEMENT: {overall_improvement:+.2f}")
            
            # Log specific improvements
            for agent in ['planner', 'analyst', 'architect', 'ticket_generator']:
                if agent in comparison:
                    agent_improvement = comparison[agent].get('overall', {}).get('improvement', 0.0)
                    if agent_improvement > 0:
                        logger.info(f"   ✅ {agent.title()}: +{agent_improvement:.2f}")
            
        else:
            logger.info("✅ NO IMPROVEMENTS NEEDED")
            workflow_output['improvements_made'] = False
        
        return workflow_output
    
    def get_quality_report(self, workflow_output: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed quality report for the workflow output"""
        logger.info("📊 GENERATING QUALITY REPORT")
        
        if 'evaluation_result' not in workflow_output:
            return {
                'error': 'No evaluation data available',
                'suggestion': 'Enable evaluation to get quality report'
            }
        
        evaluation = workflow_output['evaluation_result']
        quality_metrics = evaluation['quality_metrics']
        
        report = {
            'overall_quality': quality_metrics['overall_quality'],
            'quality_grade': self._get_quality_grade(quality_metrics['overall_quality']),
            'detailed_scores': {
                'completeness': quality_metrics['completeness'],
                'consistency': quality_metrics['consistency'],
                'clarity': quality_metrics['clarity'],
                'feasibility': quality_metrics['feasibility']
            },
            'agent_scores': {},
            'critical_issues': evaluation.get('critical_issues', []),
            'improvement_recommendations': evaluation.get('improvement_recommendations', []),
            'improvements_made': workflow_output.get('improvements_made', False)
        }
        
        # Extract agent scores
        agent_evaluations = evaluation.get('agent_evaluations', {})
        for agent, scores in agent_evaluations.items():
            report['agent_scores'][agent] = {
                score['criterion']: score['score']
                for score in scores
            }
        
        logger.info(f"📊 QUALITY REPORT: {report['quality_grade']} ({report['overall_quality']:.1f}/10)")
        
        return report
    
    def _get_quality_grade(self, score: float) -> str:
        """Convert quality score to letter grade"""
        if score >= 9.0:
            return "A+ (Excellent)"
        elif score >= 8.0:
            return "A (Very Good)"
        elif score >= 7.0:
            return "B (Good)"
        elif score >= 6.0:
            return "C (Fair)"
        elif score >= 5.0:
            return "D (Poor)"
        else:
            return "F (Very Poor)"
    
    def compare_workflows(self, workflow1: Dict[str, Any], workflow2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two workflow outputs"""
        logger.info("🔍 COMPARING WORKFLOW OUTPUTS")
        
        comparison = {
            'workflow1_quality': 0.0,
            'workflow2_quality': 0.0,
            'quality_difference': 0.0,
            'better_workflow': 'workflow1',
            'detailed_comparison': {}
        }
        
        # Get quality scores
        if 'evaluation_result' in workflow1:
            comparison['workflow1_quality'] = workflow1['evaluation_result']['quality_metrics']['overall_quality']
        
        if 'evaluation_result' in workflow2:
            comparison['workflow2_quality'] = workflow2['evaluation_result']['quality_metrics']['overall_quality']
        
        # Calculate difference
        comparison['quality_difference'] = comparison['workflow2_quality'] - comparison['workflow1_quality']
        comparison['better_workflow'] = 'workflow2' if comparison['quality_difference'] > 0 else 'workflow1'
        
        # Detailed comparison
        for i, workflow in enumerate([workflow1, workflow2], 1):
            workflow_key = f'workflow{i}'
            comparison['detailed_comparison'][workflow_key] = {
                'execution_time': workflow.get('execution_time', 0.0),
                'improvements_made': workflow.get('improvements_made', False),
                'agent_count': len([k for k in workflow.keys() if k in ['plan', 'prd', 'architecture', 'tickets']])
            }
        
        logger.info(f"📊 COMPARISON RESULT: {comparison['better_workflow']} is better by {abs(comparison['quality_difference']):.2f}")
        
        return comparison


# Factory function for easy instantiation
def create_intelligent_workflow_manager(model_name: str = "gpt-3.5-turbo", 
                                      evaluator_model: str = "gpt-4") -> IntelligentWorkflowManager:
    """Create an intelligent workflow manager with specified models"""
    return IntelligentWorkflowManager(model_name, evaluator_model)
