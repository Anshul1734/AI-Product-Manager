"""
Pydantic schemas for the Evaluator Agent output validation.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class EvaluationScore(BaseModel):
    """Individual evaluation score for a specific criterion"""
    criterion: str = Field(..., description="Evaluation criterion")
    score: float = Field(..., ge=0.0, le=10.0, description="Score from 0-10")
    reasoning: str = Field(..., description="Reasoning for the score")
    issues: List[str] = Field(default_factory=list, description="Issues identified")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    
    @validator('score')
    def validate_score(cls, v):
        if not 0.0 <= v <= 10.0:
            raise ValueError("Score must be between 0.0 and 10.0")
        return v


class QualityMetrics(BaseModel):
    """Quality metrics for the overall output"""
    completeness: float = Field(..., ge=0.0, le=10.0, description="Completeness score")
    consistency: float = Field(..., ge=0.0, le=10.0, description="Consistency score")
    clarity: float = Field(..., ge=0.0, le=10.0, description="Clarity score")
    feasibility: float = Field(..., ge=0.0, le=10.0, description="Feasibility score")
    overall_quality: float = Field(..., ge=0.0, le=10.0, description="Overall quality score")
    
    @validator('overall_quality')
    def validate_overall_quality(cls, v, values):
        if 'completeness' in values and 'consistency' in values and 'clarity' in values and 'feasibility' in values:
            # Overall quality should be average of other scores
            expected = (values['completeness'] + values['consistency'] + values['clarity'] + values['feasibility']) / 4
            if abs(v - expected) > 2.0:  # Allow some deviation
                raise ValueError("Overall quality should be close to the average of other scores")
        return v


class EvaluationResult(BaseModel):
    """Complete evaluation result with detailed analysis"""
    agent_evaluations: Dict[str, List[EvaluationScore]] = Field(..., description="Per-agent evaluation scores")
    quality_metrics: QualityMetrics = Field(..., description="Overall quality metrics")
    overall_assessment: str = Field(..., description="Overall assessment of the output")
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues that must be addressed")
    improvement_recommendations: List[str] = Field(default_factory=list, description="General improvement recommendations")
    needs_regeneration: bool = Field(..., description="Whether regeneration is needed")
    regeneration_targets: List[str] = Field(default_factory=list, description="Which agents need regeneration")
    
    @validator('agent_evaluations')
    def validate_agent_evaluations(cls, v):
        required_agents = ['planner', 'analyst', 'architect', 'ticket_generator']
        for agent in required_agents:
            if agent not in v:
                raise ValueError(f"Missing evaluation for agent: {agent}")
            if len(v[agent]) == 0:
                raise ValueError(f"No evaluation scores for agent: {agent}")
        return v


class RegenerationRequest(BaseModel):
    """Request for regenerating specific agent outputs"""
    target_agents: List[str] = Field(..., description="Which agents to regenerate")
    regeneration_reasons: Dict[str, str] = Field(..., description="Reasons for regenerating each agent")
    specific_instructions: Dict[str, List[str]] = Field(default_factory=dict, description="Specific instructions for each agent")
    quality_targets: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Target quality scores")
    
    @validator('target_agents')
    def validate_target_agents(cls, v):
        valid_agents = ['planner', 'analyst', 'architect', 'ticket_generator']
        for agent in v:
            if agent not in valid_agents:
                raise ValueError(f"Invalid target agent: {agent}")
        return v


class ImprovedOutput(BaseModel):
    """Improved output after regeneration"""
    original_output: Dict[str, Any] = Field(..., description="Original workflow output")
    improved_output: Dict[str, Any] = Field(..., description="Improved workflow output")
    evaluation_comparison: Dict[str, Dict[str, float]] = Field(..., description="Before/after quality comparison")
    improvement_summary: str = Field(..., description="Summary of improvements made")
    regeneration_attempts: int = Field(..., ge=1, le=3, description="Number of regeneration attempts")
    
    @validator('regeneration_attempts')
    def validate_regeneration_attempts(cls, v):
        if v < 1 or v > 3:
            raise ValueError("Regeneration attempts must be between 1 and 3")
        return v


class EvaluatorOutput(BaseModel):
    """Complete evaluator agent output"""
    evaluation: EvaluationResult = Field(..., description="Initial evaluation")
    regeneration_request: Optional[RegenerationRequest] = Field(None, description="Regeneration request if needed")
    improved_output: Optional[ImprovedOutput] = Field(None, description="Improved output after regeneration")
    final_assessment: str = Field(..., description="Final assessment of the process")
    total_processing_time: float = Field(..., ge=0.0, description="Total processing time in seconds")
    
    @validator('final_assessment')
    def validate_final_assessment(cls, v, values):
        if 'evaluation' in values:
            eval_result = values['evaluation']
            if eval_result.needs_regeneration and not values.get('improved_output'):
                raise ValueError("Final assessment should mention regeneration if needed")
        return v
