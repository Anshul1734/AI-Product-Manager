"""
Test script to demonstrate the memory system for conversation continuity
"""
import json
import time
from agents.memory_aware_workflow_manager import create_memory_aware_workflow_manager
from memory.memory_store import get_memory_store
from utils.logging import logger


def test_memory_aware_workflow():
    """Test the memory-aware workflow with conversation continuity"""
    
    logger.info("🧪 TESTING MEMORY-AWARE WORKFLOW SYSTEM")
    
    # Create memory-aware workflow manager
    workflow_manager = create_memory_aware_workflow_manager(
        model_name="gpt-3.5-turbo",
        evaluator_model="gpt-4"
    )
    
    # Test conversation thread
    thread_id = "test-memory-conversation-001"
    
    # First request - establish context
    logger.info("\n=== FIRST REQUEST (ESTABLISHING CONTEXT) ===")
    idea1 = "AI-powered task management tool for remote teams"
    
    try:
        result1 = workflow_manager.execute_workflow(
            idea1,
            thread_id=thread_id,
            enable_evaluation=True,
            store_in_memory=True
        )
        
        if result1.get('success', True):
            logger.info("✅ First request completed successfully")
            logger.info(f"   Product: {result1['plan']['product_name']}")
            logger.info(f"   Thread ID: {result1['thread_id']}")
            logger.info(f"   Context Used: {result1['context_used']}")
            
            # Get thread summary
            summary = workflow_manager.get_thread_summary(thread_id)
            if summary:
                logger.info(f"   Topics: {summary['topics']}")
                logger.info(f"   Average Quality: {summary['average_quality']:.1f}/10")
        else:
            logger.error("❌ First request failed")
            
    except Exception as e:
        logger.error(f"❌ First request failed: {str(e)}")
    
    # Wait a moment to ensure different timestamps
    time.sleep(2)
    
    # Second request - build on context
    logger.info("\n=== SECOND REQUEST (BUILDING ON CONTEXT) ===")
    idea2 = "Enhanced AI task scheduler with team collaboration features"
    
    try:
        result2 = workflow_manager.execute_workflow(
            idea2,
            thread_id=thread_id,
            enable_evaluation=True,
            store_in_memory=True
        )
        
        if result2.get('success', True):
            logger.info("✅ Second request completed successfully")
            logger.info(f"   Product: {result2['plan']['product_name']}")
            logger.info(f"   Context Used: {result2['context_used']}")
            
            # Check if context was used effectively
            if result2['context_used']['thread_history_count'] > 0:
                logger.info("✅ Successfully used previous conversation context")
            else:
                logger.info("ℹ️  No previous context available")
                
        else:
            logger.error("❌ Second request failed")
            
    except Exception as e:
        logger.error(f"❌ Second request failed: {str(e)}")
    
    # Wait a moment
    time.sleep(2)
    
    # Third request - similar idea for testing similarity
    logger.info("\n=== THIRD REQUEST (SIMILAR IDEA TEST) ===")
    idea3 = "AI project coordination platform for distributed teams"
    
    try:
        result3 = workflow_manager.execute_workflow(
            idea3,
            thread_id=thread_id,
            enable_evaluation=True,
            store_in_memory=True
        )
        
        if result3.get('success', True):
            logger.info("✅ Third request completed successfully")
            logger.info(f"   Product: {result3['plan']['product_name']}")
            logger.info(f"   Context Used: {result3['context_used']}")
            
            # Check if similar ideas were found
            if result3['context_used']['similar_ideas_count'] > 0:
                logger.info("✅ Successfully found and used similar ideas")
            else:
                logger.info("ℹ️  No similar ideas found")
                
        else:
            logger.error("❌ Third request failed")
            
    except Exception as e:
        logger.error(f"❌ Third request failed: {str(e)}")
    
    # Get thread history
    logger.info("\n=== THREAD HISTORY ANALYSIS ===")
    history = workflow_manager.get_thread_history(thread_id)
    logger.info(f"📚 Thread History: {len(history)} entries")
    
    for i, entry in enumerate(history[-3:], 1):  # Last 3 entries
        logger.info(f"   Entry {i}: {entry['product_idea'][:50]}...")
        logger.info(f"     Quality: {entry.get('quality_score', 'N/A')}")
        logger.info(f"     Improvements: {entry.get('improvements_made', False)}")
    
    # Get quality trends
    logger.info("\n=== QUALITY TRENDS ANALYSIS ===")
    trends = workflow_manager.get_quality_trends(thread_id)
    
    if 'error' not in trends:
        logger.info(f"📈 Quality Trends:")
        logger.info(f"   Average Quality: {trends['average_quality']:.1f}/10")
        logger.info(f"   Trend: {trends['quality_trend']}")
        logger.info(f"   Improvement Rate: {trends['improvement_rate']:.1f}%")
    else:
        logger.info("📈 No quality data available")
    
    logger.info("\n🎉 MEMORY-AWARE WORKFLOW TEST COMPLETED")


def test_similar_idea_search():
    """Test similar idea search functionality"""
    
    logger.info("\n🧪 TESTING SIMILAR IDEA SEARCH")
    
    workflow_manager = create_memory_aware_workflow_manager()
    
    # Test search with different ideas
    test_ideas = [
        "AI project management tool",
        "Task scheduling application",
        "Team collaboration platform",
        "Remote work assistant"
    ]
    
    for idea in test_ideas:
        logger.info(f"\n--- SEARCHING FOR: {idea} ---")
        
        try:
            similar_ideas = workflow_manager.search_similar_ideas(idea, limit=3)
            
            logger.info(f"🔍 Found {len(similar_ideas)} similar ideas")
            
            for i, similar in enumerate(similar_ideas, 1):
                logger.info(f"   {i}. {similar['product_idea'][:50]}...")
                logger.info(f"      Similarity: {similar['similarity']:.2f}")
                logger.info(f"      Thread: {similar['thread_id']}")
                
        except Exception as e:
            logger.error(f"❌ Search failed for '{idea}': {str(e)}")
    
    logger.info("\n🎉 SIMILAR IDEA SEARCH TEST COMPLETED")


def test_memory_store_features():
    """Test memory store features directly"""
    
    logger.info("\n🧪 TESTING MEMORY STORE FEATURES")
    
    memory_store = get_memory_store()
    
    # Get memory statistics
    stats = memory_store.get_memory_stats()
    logger.info("📊 MEMORY STORE STATISTICS:")
    logger.info(f"   Total Entries: {stats['total_entries']}")
    logger.info(f"   Total Threads: {stats['total_threads']}")
    logger.info(f"   Storage Path: {stats['storage_path']}")
    logger.info(f"   Max Memory Age: {stats['max_memory_age_days']} days")
    
    # Test conversation summary
    thread_id = "test-memory-conversation-001"
    summary = memory_store.get_thread_summary(thread_id)
    
    if summary:
        logger.info(f"\n📋 CONVERSATION SUMMARY FOR {thread_id}:")
        logger.info(f"   Created: {summary.created_at}")
        logger.info(f"   Last Updated: {summary.last_updated}")
        logger.info(f"   Total Requests: {summary.total_requests}")
        logger.info(f"   Average Quality: {summary.average_quality}")
        logger.info(f"   Topics: {summary.topics}")
    else:
        logger.info(f"\n📋 No summary found for thread {thread_id}")
    
    logger.info("\n🎉 MEMORY STORE FEATURES TEST COMPLETED")


def test_conversation_continuity():
    """Test conversation continuity across different scenarios"""
    
    logger.info("\n🧪 TESTING CONVERSATION CONTINUITY")
    
    workflow_manager = create_memory_aware_workflow_manager()
    
    # Scenario 1: Progressive refinement
    logger.info("\n=== SCENARIO 1: PROGRESSIVE REFINEMENT ===")
    thread_id = "continuity-test-001"
    
    ideas = [
        "Task management app",
        "AI-powered task management app",
        "AI-powered task management app with team collaboration",
        "AI-powered task management app with team collaboration and analytics"
    ]
    
    for i, idea in enumerate(ideas, 1):
        logger.info(f"\n--- Iteration {i}: {idea} ---")
        
        try:
            result = workflow_manager.execute_workflow(
                idea,
                thread_id=thread_id,
                enable_evaluation=False,  # Skip evaluation for speed
                store_in_memory=True
            )
            
            if result.get('success', True):
                context_used = result['context_used']
                logger.info(f"✅ Iteration {i} completed")
                logger.info(f"   Context: {context_used['thread_history_count']} history, {context_used['similar_ideas_count']} similar")
                
                # Check for progressive improvement
                if i > 1:
                    previous_context = context_used['thread_history_count'] > 0
                    logger.info(f"   Building on previous: {'Yes' if previous_context else 'No'}")
                    
            else:
                logger.error(f"❌ Iteration {i} failed")
                
        except Exception as e:
            logger.error(f"❌ Iteration {i} failed: {str(e)}")
        
        time.sleep(1)  # Small delay between requests
    
    # Scenario 2: Thread switching
    logger.info("\n=== SCENARIO 2: THREAD SWITCHING ===")
    
    thread_a = "thread-switch-a"
    thread_b = "thread-switch-b"
    
    # Request in thread A
    logger.info("\n--- Request in Thread A ---")
    try:
        result_a = workflow_manager.execute_workflow(
            "Project management dashboard",
            thread_id=thread_a,
            enable_evaluation=False,
            store_in_memory=True
        )
        logger.info("✅ Thread A request completed")
    except Exception as e:
        logger.error(f"❌ Thread A request failed: {str(e)}")
    
    # Request in thread B
    logger.info("\n--- Request in Thread B ---")
    try:
        result_b = workflow_manager.execute_workflow(
            "Customer relationship management system",
            thread_id=thread_b,
            enable_evaluation=False,
            store_in_memory=True
        )
        logger.info("✅ Thread B request completed")
    except Exception as e:
        logger.error(f"❌ Thread B request failed: {str(e)}")
    
    # Back to thread A
    logger.info("\n--- Back to Thread A ---")
    try:
        result_a2 = workflow_manager.execute_workflow(
            "Enhanced project management dashboard",
            thread_id=thread_a,
            enable_evaluation=False,
            store_in_memory=True
        )
        
        if result_a2.get('success', True):
            context_used = result_a2['context_used']
            logger.info("✅ Thread A continuation completed")
            logger.info(f"   Context from Thread A: {context_used['thread_history_count']} entries")
            
    except Exception as e:
        logger.error(f"❌ Thread A continuation failed: {str(e)}")
    
    logger.info("\n🎉 CONVERSATION CONTINUITY TEST COMPLETED")


if __name__ == "__main__":
    test_memory_aware_workflow()
    test_similar_idea_search()
    test_memory_store_features()
    test_conversation_continuity()
