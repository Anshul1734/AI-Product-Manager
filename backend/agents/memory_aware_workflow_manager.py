"""
Memory-aware workflow manager that maintains conversation continuity and context.
"""
from typing import Dict, Any, Optional, List
import time
from .memory_aware_agents import (
    MemoryAwarePlannerAgent,
    MemoryAwareAnalystAgent,
    MemoryAwareArchitectAgent,
    MemoryAwareTicketGeneratorAgent
)
from .evaluator_agent import EvaluatorAgent
from memory.memory_store import get_memory_store, create_memory_entry
from utils.logging import logger


class MemoryAwareWorkflowManager:
    """Workflow manager with memory awareness for conversation continuity"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", evaluator_model: str = "gpt-4"):
        # Memory-aware agents
        self.planner = MemoryAwarePlannerAgent(model_name)
        self.analyst = MemoryAwareAnalystAgent(model_name)
        self.architect = MemoryAwareArchitectAgent(model_name)
        self.ticket_generator = MemoryAwareTicketGeneratorAgent(model_name)
        
        # Evaluator for quality assessment
        self.evaluator = EvaluatorAgent(evaluator_model)
        
        # Memory store
        self.memory_store = get_memory_store()
        
    def execute_workflow(self, product_idea: str, thread_id: Optional[str] = None, 
                         enable_evaluation: bool = True, store_in_memory: bool = True) -> Dict[str, Any]:
        """Execute the complete memory-aware workflow"""
        logger.info(f"🧠 STARTING MEMORY-AWARE WORKFLOW EXECUTION")
        logger.info(f"   Product Idea: {product_idea[:100]}...")
        logger.info(f"   Thread ID: {thread_id}")
        logger.info(f"   Evaluation Enabled: {enable_evaluation}")
        logger.info(f"   Store in Memory: {store_in_memory}")
        
        # Generate thread ID if not provided
        if not thread_id:
            thread_id = f"thread_{int(time.time())}_{hash(product_idea) % 10000}"
            logger.info(f"   Generated Thread ID: {thread_id}")
        
        start_time = time.time()
        agent_times = {}
        
        try:
            # Get conversation context
            logger.info("📋 PHASE 1: RETRIEVING CONVERSATION CONTEXT")
            context = self.memory_store.get_relevant_context(thread_id, product_idea)
            
            # Log context information
            if context['thread_history']:
                logger.info(f"   📚 Found {len(context['thread_history'])} previous entries")
            if context['similar_ideas']:
                logger.info(f"   🔍 Found {len(context['similar_ideas'])} similar ideas")
            if context['thread_summary']:
                logger.info(f"   📋 Thread summary available with {len(context['thread_summary'].get('topics', []))} topics")
            
            # Step 1: Execute memory-aware workflow
            logger.info("📋 PHASE 2: MEMORY-AWARE WORKFLOW EXECUTION")
            workflow_output = self._execute_memory_aware_workflow(product_idea, thread_id, agent_times)
            
            # Step 3: Evaluate and improve if enabled
            if enable_evaluation:
                logger.info("📋 PHASE 3: EVALUATION AND IMPROVEMENT")
                final_output = self._evaluate_and_improve(workflow_output, agent_times)
            else:
                logger.info("📋 PHASE 3: SKIPPED (evaluation disabled)")
                final_output = workflow_output
            
            # Step 4: Store in memory if enabled
            if store_in_memory:
                logger.info("📋 PHASE 4: STORING IN MEMORY")
                self._store_in_memory(thread_id, product_idea, final_output, agent_times, enable_evaluation)
            
            # Step 5: Prepare final result
            total_time = time.time() - start_time
            
            workflow_result = {
                'plan': final_output['plan'],
                'prd': final_output['prd'],
                'architecture': final_output['architecture'],
                'tickets': final_output['tickets'],
                'execution_time': total_time,
                'agent_times': agent_times,
                'thread_id': thread_id,
                'evaluation_enabled': enable_evaluation,
                'memory_enabled': store_in_memory,
                'context_used': {
                    'thread_history_count': len(context['thread_history']),
                    'similar_ideas_count': len(context['similar_ideas']),
                    'has_summary': context['thread_summary'] is not None
                }
            }
            
            # Add evaluation results if available
            if enable_evaluation and 'evaluation_result' in final_output:
                workflow_result['evaluation'] = final_output['evaluation_result']
                workflow_result['improvements_made'] = final_output.get('improvements_made', False)
            
            logger.info(f"✅ MEMORY-AWARE WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info(f"📊 EXECUTION SUMMARY:")
            logger.info(f"   - Total Time: {total_time:.2f}s")
            logger.info(f"   - Thread ID: {thread_id}")
            logger.info(f"   - Context Used: {len(context['thread_history'])} history, {len(context['similar_ideas'])} similar")
            logger.info(f"   - Evaluation: {'Enabled' if enable_evaluation else 'Disabled'}")
            logger.info(f"   - Memory: {'Stored' if store_in_memory else 'Not stored'}")
            
            return workflow_result
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ MEMORY-AWARE WORKFLOW FAILED")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Execution Time: {total_time:.2f}s")
            
            # Return error response
            from schemas.agent_validation import create_fallback_output
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': total_time,
                'thread_id': thread_id,
                'evaluation_enabled': enable_evaluation,
                'memory_enabled': store_in_memory,
                'fallback_data': {
                    'plan': create_fallback_output('planner'),
                    'prd': create_fallback_output('analyst'),
                    'architecture': create_fallback_output('architect'),
                    'tickets': create_fallback_output('ticket_generator')
                }
            }
    
    def _execute_memory_aware_workflow(self, product_idea: str, thread_id: str, agent_times: Dict[str, float]) -> Dict[str, Any]:
        """Execute the memory-aware workflow"""
        
        # Step 1: Memory-aware Planner Agent
        step_start = time.time()
        plan = self.planner.execute(product_idea, thread_id)
        agent_times['planner'] = time.time() - step_start
        
        # Step 2: Memory-aware Analyst Agent
        step_start = time.time()
        prd = self.analyst.execute(plan, thread_id)
        agent_times['analyst'] = time.time() - step_start
        
        # Step 3: Memory-aware Architect Agent
        step_start = time.time()
        architecture = self.architect.execute(prd, thread_id)
        agent_times['architect'] = time.time() - step_start
        
        # Step 4: Memory-aware Ticket Generator Agent
        step_start = time.time()
        tickets = self.ticket_generator.execute(prd, architecture, thread_id)
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
            
        else:
            logger.info("✅ NO IMPROVEMENTS NEEDED")
            workflow_output['improvements_made'] = False
        
        return workflow_output
    
    def _store_in_memory(self, thread_id: str, product_idea: str, workflow_output: Dict[str, Any], 
                       agent_times: Dict[str, float], evaluation_enabled: bool):
        """Store the workflow result in memory"""
        
        try:
            # Calculate quality score
            quality_score = None
            if 'evaluation_result' in workflow_output:
                quality_score = workflow_output['evaluation_result']['quality_metrics']['overall_quality']
            
            # Create memory entry
            memory_entry = create_memory_entry(
                thread_id=thread_id,
                product_idea=product_idea,
                workflow_output=workflow_output,
                execution_time=sum(agent_times.values()),
                quality_score=quality_score,
                improvements_made=workflow_output.get('improvements_made', False),
                metadata={
                    'evaluation_enabled': evaluation_enabled,
                    'agent_times': agent_times,
                    'context_used': True
                }
            )
            
            # Store in memory
            success = self.memory_store.store_entry(memory_entry)
            
            if success:
                logger.info(f"💾 Successfully stored workflow result in memory")
                logger.info(f"   Thread: {thread_id}")
                logger.info(f"   Quality: {quality_score:.1f}/10" if quality_score else "   Quality: Not evaluated")
            else:
                logger.warning("⚠️  Failed to store workflow result in memory")
                
        except Exception as e:
            logger.error(f"❌ Memory storage failed: {str(e)}")
    
    def get_thread_summary(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a conversation thread"""
        logger.info(f"📋 GETTING THREAD SUMMARY: {thread_id}")
        
        try:
            summary = self.memory_store.get_thread_summary(thread_id)
            
            if summary:
                summary_dict = {
                    'thread_id': summary.thread_id,
                    'created_at': summary.created_at.isoformat(),
                    'last_updated': summary.last_updated.isoformat(),
                    'total_requests': summary.total_requests,
                    'average_quality': summary.average_quality,
                    'topics': summary.topics,
                    'key_insights': summary.key_insights
                }
                logger.info(f"📋 Retrieved summary for thread {thread_id}")
                return summary_dict
            else:
                logger.info(f"📋 No summary found for thread {thread_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get thread summary: {str(e)}")
            return None
    
    def get_thread_history(self, thread_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history for a thread"""
        logger.info(f"📚 GETTING THREAD HISTORY: {thread_id}")
        
        try:
            entries = self.memory_store.get_thread_history(thread_id, limit)
            
            history = []
            for entry in entries:
                entry_dict = {
                    'timestamp': entry.timestamp.isoformat(),
                    'product_idea': entry.product_idea,
                    'execution_time': entry.execution_time,
                    'quality_score': entry.quality_score,
                    'improvements_made': entry.improvements_made,
                    'metadata': entry.metadata
                }
                history.append(entry_dict)
            
            logger.info(f"📚 Retrieved {len(history)} entries for thread {thread_id}")
            return history
            
        except Exception as e:
            logger.error(f"❌ Failed to get thread history: {str(e)}")
            return []
    
    def search_similar_ideas(self, product_idea: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar product ideas in memory"""
        logger.info(f"🔍 SEARCHING SIMILAR IDEAS: {product_idea[:50]}...")
        
        try:
            similar_entries = self.memory_store.search_similar_ideas(product_idea, limit)
            
            results = []
            for entry, similarity in similar_entries:
                result = {
                    'thread_id': entry.thread_id,
                    'timestamp': entry.timestamp.isoformat(),
                    'product_idea': entry.product_idea,
                    'similarity': similarity,
                    'quality_score': entry.quality_score,
                    'execution_time': entry.execution_time
                }
                results.append(result)
            
            logger.info(f"🔍 Found {len(results)} similar ideas")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to search similar ideas: {str(e)}")
            return []
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        logger.info("📊 GETTING MEMORY STATISTICS")
        
        try:
            stats = self.memory_store.get_memory_stats()
            logger.info(f"📊 Memory stats: {stats['total_entries']} entries, {stats['total_threads']} threads")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get memory stats: {str(e)}")
            return {}
    
    def get_quality_trends(self, thread_id: str) -> Dict[str, Any]:
        """Analyze quality trends for a thread"""
        logger.info(f"📈 ANALYZING QUALITY TRENDS: {thread_id}")
        
        try:
            trends = self.memory_store.get_quality_trends(thread_id)
            
            if 'error' not in trends:
                logger.info(f"📈 Quality trends: {trends['average_quality']:.1f} average, {trends['quality_trend']} trend")
            else:
                logger.info(f"📈 No quality data available for thread {thread_id}")
            
            return trends
            
        except Exception as e:
            logger.error(f"❌ Failed to get quality trends: {str(e)}")
            return {'error': str(e)}


# Factory function for easy instantiation
def create_memory_aware_workflow_manager(model_name: str = "gpt-3.5-turbo", 
                                         evaluator_model: str = "gpt-4") -> MemoryAwareWorkflowManager:
    """Create a memory-aware workflow manager with specified models"""
    return MemoryAwareWorkflowManager(model_name, evaluator_model)
