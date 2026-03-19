"""
Evaluator Agent that reviews and improves workflow outputs through iterative refinement.
"""
from typing import Dict, Any, List, Optional, Tuple
import json
import time
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
from schemas.evaluator import (
    EvaluationResult,
    EvaluationScore,
    QualityMetrics,
    RegenerationRequest,
    ImprovedOutput,
    EvaluatorOutput
)
from schemas.agent_validation import AgentValidationFactory
from utils.logging import logger


class EvaluatorAgent:
    """Intelligent evaluator agent that reviews and improves workflow outputs"""
    
    def __init__(self, model_name: str = "gpt-4"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.0-pro")
        self.max_regeneration_attempts = 2
        self.quality_threshold = 7.0  # Minimum acceptable quality score
        
    def _create_evaluation_prompt(self, workflow_output: Dict[str, Any]) -> str:
        """Create a comprehensive evaluation prompt"""
        
        plan = workflow_output.get('plan', {})
        prd = workflow_output.get('prd', {})
        architecture = workflow_output.get('architecture', {})
        tickets = workflow_output.get('tickets', {})
        
        return f"""
You are an expert AI Product Manager evaluator. Your task is to comprehensively evaluate a complete workflow output and identify areas for improvement.

WORKFLOW OUTPUT TO EVALUATE:

=== PLANNER OUTPUT ===
Product Name: {plan.get('product_name', 'N/A')}
Problem Statement: {plan.get('problem_statement', 'N/A')}
Target Users: {plan.get('target_users', [])}
Core Goals: {plan.get('core_goals', [])}
Key Features: {plan.get('key_features_high_level', [])}

=== ANALYST OUTPUT ===
Problem Statement: {prd.get('problem_statement', 'N/A')}
Target Users: {prd.get('target_users', [])}
User Personas: {len(prd.get('user_personas', []))} personas
User Stories: {len(prd.get('user_stories', []))} stories
Success Metrics: {len(prd.get('success_metrics', []))} metrics

=== ARCHITECT OUTPUT ===
System Design: {architecture.get('system_design', 'N/A')}
Tech Stack: {list(architecture.get('tech_stack', {}).keys())}
Components: {architecture.get('architecture_components', [])}
API Endpoints: {len(architecture.get('api_endpoints', []))} endpoints
Database Tables: {len(architecture.get('database_schema', []))} tables

=== TICKET OUTPUT ===
Epics: {len(tickets.get('epics', []))} epics
Total Stories: {sum(len(epic.get('stories', [])) for epic in tickets.get('epics', []))}
Total Tasks: {sum(len(story.get('tasks', [])) for epic in tickets.get('epics', []) for story in epic.get('stories', []))}

EVALUATION CRITERIA:

For each agent (planner, analyst, architect, ticket_generator), evaluate:
1. Completeness (0-10): Are all required fields present and well-developed?
2. Consistency (0-10): Do the outputs align with each other and the original idea?
3. Clarity (0-10): Is the language clear, specific, and actionable?
4. Feasibility (0-10): Are the suggestions realistic and implementable?

For each criterion, provide:
- Score (0-10)
- Reasoning (why this score)
- Issues (specific problems found)
- Suggestions (how to improve)

QUALITY THRESHOLDS:
- 8.0-10.0: Excellent quality
- 6.0-7.9: Good quality, minor improvements needed
- 4.0-5.9: Fair quality, significant improvements needed
- 0.0-3.9: Poor quality, major improvements needed

Please respond with a JSON object containing:
{{
    "agent_evaluations": {{
        "planner": [
            {{
                "criterion": "completeness",
                "score": 8.5,
                "reasoning": "All required fields are present and well-developed",
                "issues": [],
                "suggestions": []
            }},
            {{
                "criterion": "consistency",
                "score": 7.0,
                "reasoning": "Good alignment with other outputs",
                "issues": ["Minor inconsistency with analyst output"],
                "suggestions": ["Align problem statement with analyst output"]
            }},
            {{
                "criterion": "clarity",
                "score": 8.0,
                "reasoning": "Clear and specific language",
                "issues": [],
                "suggestions": []
            }},
            {{
                "criterion": "feasibility",
                "score": 7.5,
                "reasoning": "Realistic suggestions",
                "issues": ["Some features may be overly ambitious"],
                "suggestions": ["Consider phased implementation"]
            }}
        ],
        "analyst": [...],
        "architect": [...],
        "ticket_generator": [...]
    }},
    "quality_metrics": {{
        "completeness": 7.5,
        "consistency": 7.0,
        "clarity": 7.8,
        "feasibility": 7.2,
        "overall_quality": 7.4
    }},
    "overall_assessment": "The workflow output is of good quality with minor areas for improvement...",
    "critical_issues": [],
    "improvement_recommendations": ["Consider aligning problem statements across agents"],
    "needs_regeneration": false,
    "regeneration_targets": []
}}

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.
"""
    
    def _create_regeneration_prompt(self, workflow_output: Dict[str, Any], 
                                 evaluation: EvaluationResult, 
                                 regeneration_request: RegenerationRequest) -> str:
        """Create a prompt for regenerating specific agent outputs"""
        
        target_agents = regeneration_request.target_agents
        reasons = regeneration_request.regeneration_reasons
        instructions = regeneration_request.specific_instructions
        
        prompt = f"""
You are an expert AI Product Manager tasked with improving specific agent outputs based on evaluation feedback.

ORIGINAL WORKFLOW OUTPUT:
{json.dumps(workflow_output, indent=2)}

EVALUATION FEEDBACK:
{json.dumps(evaluation.dict(), indent=2)}

REGENERATION REQUEST:
Target Agents: {', '.join(target_agents)}
Reasons: {json.dumps(reasons, indent=2)}
Specific Instructions: {json.dumps(instructions, indent=2)}

For each target agent, regenerate the output addressing:
1. All critical issues identified in the evaluation
2. Specific improvement suggestions provided
3. Any additional instructions in the regeneration request

REGENERATION GUIDELINES:
- Maintain consistency with other agent outputs
- Ensure all required fields are present and complete
- Use clear, specific, and actionable language
- Keep suggestions realistic and feasible
- Follow the original schema structure

Please respond with a JSON object containing the improved outputs for the target agents:

{{
    "improved_outputs": {{
        "planner": {{ ... }} if planner is target,
        "analyst": {{ ... }} if analyst is target,
        "architect": {{ ... }} if architect is target,
        "ticket_generator": {{ ... }} if ticket_generator is target
    }},
    "improvements_made": [
        "Aligned problem statement across all agents",
        "Added missing user personas",
        "Improved technical feasibility"
    ],
    "quality_improvement": "Significant improvement in consistency and completeness"
}}

Respond ONLY with valid JSON. No explanations, no markdown, just the JSON object.
"""
        
        return prompt
    
    def _evaluate_output(self, workflow_output: Dict[str, Any]) -> EvaluationResult:
        """Evaluate the workflow output"""
        logger.info("🔍 EVALUATING WORKFLOW OUTPUT")
        
        try:
            # Generate evaluation
            prompt = self._create_evaluation_prompt(workflow_output)
            messages = [
                SystemMessage(content="You are an expert evaluator who always responds with valid JSON."),
                HumanMessage(content=prompt)
            ]
            
            start_time = time.time()
            response = self.model.generate_content(full_prompt)
            execution_time = time.time() - start_time
            
            raw_output = response.text
            logger.info(f"   Evaluation completed in {execution_time:.2f}s")
            
            # Parse and validate the evaluation
            cleaned_output = self._clean_json_output(raw_output)
            evaluation_data = json.loads(cleaned_output)
            
            # Validate against schema
            evaluation = EvaluationResult(**evaluation_data)
            
            logger.info(f"   Overall Quality Score: {evaluation.quality_metrics.overall_quality}/10")
            logger.info(f"   Needs Regeneration: {evaluation.needs_regeneration}")
            
            return evaluation
            
        except Exception as e:
            logger.error(f"   ❌ Evaluation failed: {str(e)}")
            # Return a minimal evaluation that triggers regeneration
            return self._create_fallback_evaluation(workflow_output)
    
    def _create_fallback_evaluation(self, workflow_output: Dict[str, Any]) -> EvaluationResult:
        """Create a fallback evaluation when the main evaluation fails"""
        logger.warning("   🔄 Using fallback evaluation")
        
        # Create basic evaluation scores
        agent_evaluations = {}
        for agent in ['planner', 'analyst', 'architect', 'ticket_generator']:
            agent_evaluations[agent] = [
                EvaluationScore(
                    criterion="completeness",
                    score=5.0,
                    reasoning="Fallback evaluation - unable to perform detailed assessment",
                    issues=["Evaluation system error"],
                    suggestions=["Retry evaluation"]
                ),
                EvaluationScore(
                    criterion="consistency",
                    score=5.0,
                    reasoning="Fallback evaluation - unable to perform detailed assessment",
                    issues=["Evaluation system error"],
                    suggestions=["Retry evaluation"]
                ),
                EvaluationScore(
                    criterion="clarity",
                    score=5.0,
                    reasoning="Fallback evaluation - unable to perform detailed assessment",
                    issues=["Evaluation system error"],
                    suggestions=["Retry evaluation"]
                ),
                EvaluationScore(
                    criterion="feasibility",
                    score=5.0,
                    reasoning="Fallback evaluation - unable to perform detailed assessment",
                    issues=["Evaluation system error"],
                    suggestions=["Retry evaluation"]
                )
            ]
        
        quality_metrics = QualityMetrics(
            completeness=5.0,
            consistency=5.0,
            clarity=5.0,
            feasibility=5.0,
            overall_quality=5.0
        )
        
        return EvaluationResult(
            agent_evaluations=agent_evaluations,
            quality_metrics=quality_metrics,
            overall_assessment="Fallback evaluation due to system error",
            critical_issues=["Evaluation system malfunction"],
            improvement_recommendations=["Fix evaluation system"],
            needs_regeneration=True,
            regeneration_targets=['planner', 'analyst', 'architect', 'ticket_generator']
        )
    
    def _regenerate_outputs(self, workflow_output: Dict[str, Any], 
                           evaluation: EvaluationResult,
                           regeneration_request: RegenerationRequest) -> Dict[str, Any]:
        """Regenerate specific agent outputs"""
        logger.info(f"🔄 REGENERATING OUTPUTS FOR: {', '.join(regeneration_request.target_agents)}")
        
        try:
            # Generate regeneration
            prompt = self._create_regeneration_prompt(workflow_output, evaluation, regeneration_request)
            messages = [
                SystemMessage(content="You are an expert improver who always responds with valid JSON."),
                HumanMessage(content=prompt)
            ]
            
            start_time = time.time()
            response = self.model.generate_content(full_prompt)
            execution_time = time.time() - start_time
            
            raw_output = response.text
            logger.info(f"   Regeneration completed in {execution_time:.2f}s")
            
            # Parse and validate the regeneration
            cleaned_output = self._clean_json_output(raw_output)
            regeneration_data = json.loads(cleaned_output)
            
            # Update workflow output with improved outputs
            improved_output = workflow_output.copy()
            improved_outputs = regeneration_data.get('improved_outputs', {})
            
            for agent, improved_data in improved_outputs.items():
                if agent in improved_output:
                    # Validate the improved output
                    try:
                        validated_output = AgentValidationFactory.validate_agent_output(agent, json.dumps(improved_data))
                        improved_output[agent] = validated_output
                        logger.info(f"   ✅ {agent.title()} output improved and validated")
                    except Exception as e:
                        logger.warning(f"   ⚠️  {agent.title()} output validation failed: {str(e)}")
                        logger.warning(f"   🔄 Keeping original {agent.title()} output")
            
            return improved_output
            
        except Exception as e:
            logger.error(f"   ❌ Regeneration failed: {str(e)}")
            return workflow_output
    
    def _compare_quality(self, original_output: Dict[str, Any], 
                        improved_output: Dict[str, Any],
                        original_evaluation: EvaluationResult) -> Dict[str, Dict[str, float]]:
        """Compare quality scores before and after improvement"""
        logger.info("📊 COMPARING QUALITY SCORES")
        
        # Re-evaluate the improved output
        improved_evaluation = self._evaluate_output(improved_output)
        
        comparison = {}
        for agent in ['planner', 'analyst', 'architect', 'ticket_generator']:
            comparison[agent] = {}
            
            # Compare each criterion
            original_scores = {score.criterion: score.score for score in original_evaluation.agent_evaluations[agent]}
            improved_scores = {score.criterion: score.score for score in improved_evaluation.agent_evaluations[agent]}
            
            for criterion in original_scores:
                original_score = original_scores.get(criterion, 0.0)
                improved_score = improved_scores.get(criterion, 0.0)
                improvement = improved_score - original_score
                
                comparison[agent][criterion] = {
                    'original': original_score,
                    'improved': improved_score,
                    'improvement': improvement
                }
        
        # Add overall quality comparison
        comparison['overall'] = {
            'original': original_evaluation.quality_metrics.overall_quality,
            'improved': improved_evaluation.quality_metrics.overall_quality,
            'improvement': improved_evaluation.quality_metrics.overall_quality - original_evaluation.quality_metrics.overall_quality
        }
        
        logger.info(f"   Overall quality improvement: {comparison['overall']['improvement']:+.2f}")
        
        return comparison
    
    def _clean_json_output(self, raw_output: str) -> str:
        """Clean raw LLM output to extract valid JSON"""
        import re
        
        # Remove common LLM artifacts
        cleaned = raw_output.strip()
        
        # Remove markdown code blocks
        cleaned = re.sub(r'```json\s*', '', cleaned)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        
        # Find JSON boundaries
        json_start = cleaned.find('{')
        json_end = cleaned.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            cleaned = cleaned[json_start:json_end + 1]
        
        # Fix common JSON issues
        cleaned = cleaned.replace("'", '"')  # Single quotes to double quotes
        cleaned = re.sub(r',\s*}', '}', cleaned)  # Trailing commas
        cleaned = re.sub(r',\s*]', ']', cleaned)  # Trailing commas in arrays
        
        return cleaned
    
    def execute(self, workflow_output: Dict[str, Any]) -> EvaluatorOutput:
        """Execute the complete evaluation and improvement process"""
        logger.info("🚀 STARTING EVALUATOR AGENT")
        
        start_time = time.time()
        
        try:
            # Step 1: Evaluate the original output
            logger.info("📋 STEP 1: EVALUATING ORIGINAL OUTPUT")
            evaluation = self._evaluate_output(workflow_output)
            
            # Step 2: Determine if regeneration is needed
            regeneration_request = None
            improved_output_data = None
            
            if evaluation.needs_regeneration and evaluation.quality_metrics.overall_quality < self.quality_threshold:
                logger.info("📋 STEP 2: REGENERATING OUTPUTS")
                
                # Create regeneration request
                regeneration_request = RegenerationRequest(
                    target_agents=evaluation.regeneration_targets,
                    regeneration_reasons={
                        agent: f"Quality score below threshold ({evaluation.quality_metrics.overall_quality})"
                        for agent in evaluation.regeneration_targets
                    },
                    specific_instructions={
                        agent: [
                            issue for score in evaluation.agent_evaluations[agent]
                            for issue in score.issues
                        ]
                        for agent in evaluation.regeneration_targets
                    }
                )
                
                # Regenerate outputs
                improved_workflow_output = self._regenerate_outputs(workflow_output, evaluation, regeneration_request)
                
                # Compare quality
                quality_comparison = self._compare_quality(workflow_output, improved_workflow_output, evaluation)
                
                # Create improved output data
                improved_output_data = ImprovedOutput(
                    original_output=workflow_output,
                    improved_output=improved_workflow_output,
                    evaluation_comparison=quality_comparison,
                    improvement_summary=f"Improved outputs for {', '.join(regeneration_request.target_agents)}",
                    regeneration_attempts=1
                )
                
                logger.info("✅ OUTPUT REGENERATION COMPLETED")
            
            # Step 3: Create final output
            total_time = time.time() - start_time
            
            if improved_output_data:
                final_assessment = f"Workflow output improved from {evaluation.quality_metrics.overall_quality:.1f} to {improved_output_data.evaluation_comparison['overall']['improved']:.1f} quality score"
                final_output = improved_output_data.improved_output
            else:
                final_assessment = f"Workflow output quality: {evaluation.quality_metrics.overall_quality:.1f}/10. No regeneration needed."
                final_output = workflow_output
            
            evaluator_output = EvaluatorOutput(
                evaluation=evaluation,
                regeneration_request=regeneration_request,
                improved_output=improved_output_data,
                final_assessment=final_assessment,
                total_processing_time=total_time
            )
            
            logger.info(f"✅ EVALUATOR COMPLETED IN {total_time:.2f}s")
            logger.info(f"📊 FINAL ASSESSMENT: {final_assessment}")
            
            return evaluator_output
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ EVALUATOR FAILED: {str(e)}")
            
            # Return error output
            return EvaluatorOutput(
                evaluation=self._create_fallback_evaluation(workflow_output),
                regeneration_request=None,
                improved_output=None,
                final_assessment=f"Evaluation failed: {str(e)}",
                total_processing_time=total_time
            )
