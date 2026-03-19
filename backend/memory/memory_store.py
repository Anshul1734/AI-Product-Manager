"""
Memory store for managing conversation history and context persistence.
"""
from typing import Dict, Any, List, Optional, Tuple
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from collections import defaultdict
from utils.logging import logger


@dataclass
class MemoryEntry:
    """Single memory entry representing a conversation turn"""
    thread_id: str
    timestamp: datetime
    product_idea: str
    workflow_output: Dict[str, Any]
    execution_time: float
    quality_score: Optional[float] = None
    improvements_made: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'thread_id': self.thread_id,
            'timestamp': self.timestamp.isoformat(),
            'product_idea': self.product_idea,
            'workflow_output': self.workflow_output,
            'execution_time': self.execution_time,
            'quality_score': self.quality_score,
            'improvements_made': self.improvements_made,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary"""
        return cls(
            thread_id=data['thread_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            product_idea=data['product_idea'],
            workflow_output=data['workflow_output'],
            execution_time=data['execution_time'],
            quality_score=data.get('quality_score'),
            improvements_made=data.get('improvements_made', False),
            metadata=data.get('metadata')
        )


@dataclass
class ConversationSummary:
    """Summary of a conversation thread"""
    thread_id: str
    created_at: datetime
    last_updated: datetime
    total_requests: int
    average_quality: Optional[float] = None
    topics: List[str] = None
    key_insights: List[str] = None
    
    def __post_init__(self):
        if self.topics is None:
            self.topics = []
        if self.key_insights is None:
            self.key_insights = []


class MemoryStore:
    """Thread-safe memory store for conversation persistence"""
    
    def __init__(self, storage_path: Optional[str] = None, max_memory_age_days: int = 30):
        self.storage_path = Path(storage_path) if storage_path else Path("memory_store.json")
        self.max_memory_age_days = max_memory_age_days
        self._lock = threading.RLock()
        
        # In-memory storage
        self._entries: Dict[str, List[MemoryEntry]] = defaultdict(list)
        self._summaries: Dict[str, ConversationSummary] = {}
        
        # Load existing data
        self._load_memory()
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def store_entry(self, entry: MemoryEntry) -> bool:
        """Store a new memory entry"""
        with self._lock:
            try:
                # Add to in-memory storage
                self._entries[entry.thread_id].append(entry)
                
                # Update conversation summary
                self._update_summary(entry.thread_id)
                
                # Save to disk
                self._save_memory()
                
                logger.info(f"💾 Stored memory entry for thread {entry.thread_id}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to store memory entry: {str(e)}")
                return False
    
    def get_thread_history(self, thread_id: str, limit: Optional[int] = None) -> List[MemoryEntry]:
        """Get conversation history for a thread"""
        with self._lock:
            entries = self._entries.get(thread_id, [])
            
            if limit:
                entries = entries[-limit:]
            
            logger.info(f"📚 Retrieved {len(entries)} entries for thread {thread_id}")
            return entries
    
    def get_thread_summary(self, thread_id: str) -> Optional[ConversationSummary]:
        """Get conversation summary for a thread"""
        with self._lock:
            summary = self._summaries.get(thread_id)
            
            if summary:
                logger.info(f"📋 Retrieved summary for thread {thread_id}")
            else:
                logger.info(f"📋 No summary found for thread {thread_id}")
            
            return summary
    
    def search_similar_ideas(self, product_idea: str, limit: int = 5) -> List[Tuple[MemoryEntry, float]]:
        """Search for similar product ideas in memory"""
        with self._lock:
            similar_entries = []
            
            for thread_entries in self._entries.values():
                for entry in thread_entries:
                    similarity = self._calculate_similarity(product_idea, entry.product_idea)
                    if similarity > 0.3:  # Similarity threshold
                        similar_entries.append((entry, similarity))
            
            # Sort by similarity and limit results
            similar_entries.sort(key=lambda x: x[1], reverse=True)
            similar_entries = similar_entries[:limit]
            
            logger.info(f"🔍 Found {len(similar_entries)} similar ideas for: {product_idea[:50]}...")
            return similar_entries
    
    def get_relevant_context(self, thread_id: str, current_idea: str) -> Dict[str, Any]:
        """Get relevant context for a new request"""
        with self._lock:
            context = {
                'thread_history': [],
                'similar_ideas': [],
                'thread_summary': None,
                'recommendations': []
            }
            
            # Get thread history
            thread_entries = self.get_thread_history(thread_id, limit=3)
            context['thread_history'] = [entry.to_dict() for entry in thread_entries]
            
            # Get thread summary
            summary = self.get_thread_summary(thread_id)
            if summary:
                context['thread_summary'] = asdict(summary)
            
            # Search for similar ideas
            similar_ideas = self.search_similar_ideas(current_idea, limit=3)
            context['similar_ideas'] = [
                {
                    'entry': entry.to_dict(),
                    'similarity': similarity,
                    'relevant_insights': self._extract_relevant_insights(entry, current_idea)
                }
                for entry, similarity in similar_ideas
            ]
            
            # Generate recommendations
            context['recommendations'] = self._generate_recommendations(context)
            
            logger.info(f"🧠 Generated context for thread {thread_id} with {len(context['similar_ideas'])} similar ideas")
            return context
    
    def get_quality_trends(self, thread_id: str) -> Dict[str, Any]:
        """Analyze quality trends for a thread"""
        with self._lock:
            entries = self._entries.get(thread_id, [])
            
            if not entries:
                return {'error': 'No entries found for thread'}
            
            quality_scores = [entry.quality_score for entry in entries if entry.quality_score is not None]
            
            if not quality_scores:
                return {'error': 'No quality scores available'}
            
            trends = {
                'total_requests': len(entries),
                'quality_scores': quality_scores,
                'average_quality': sum(quality_scores) / len(quality_scores),
                'quality_trend': 'improving' if len(quality_scores) > 1 and quality_scores[-1] > quality_scores[0] else 'stable',
                'improvement_rate': (quality_scores[-1] - quality_scores[0]) / quality_scores[0] * 100 if len(quality_scores) > 1 else 0,
                'best_request': max(entries, key=lambda x: x.quality_score or 0).product_idea if quality_scores else None
            }
            
            logger.info(f"📈 Analyzed quality trends for thread {thread_id}")
            return trends
    
    def cleanup_old_entries(self) -> int:
        """Remove entries older than max_memory_age_days"""
        with self._lock:
            cutoff_date = datetime.now() - timedelta(days=self.max_memory_age_days)
            removed_count = 0
            
            for thread_id in list(self._entries.keys()):
                entries = self._entries[thread_id]
                original_count = len(entries)
                
                # Remove old entries
                self._entries[thread_id] = [
                    entry for entry in entries 
                    if entry.timestamp > cutoff_date
                ]
                
                removed_count += original_count - len(self._entries[thread_id])
                
                # Remove thread if empty
                if not self._entries[thread_id]:
                    del self._entries[thread_id]
                    if thread_id in self._summaries:
                        del self._summaries[thread_id]
            
            if removed_count > 0:
                self._save_memory()
                logger.info(f"🧹 Cleaned up {removed_count} old memory entries")
            
            return removed_count
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        with self._lock:
            total_entries = sum(len(entries) for entries in self._entries.values())
            total_threads = len(self._entries)
            
            quality_scores = [
                entry.quality_score 
                for entries in self._entries.values() 
                for entry in entries 
                if entry.quality_score is not None
            ]
            
            stats = {
                'total_entries': total_entries,
                'total_threads': total_threads,
                'average_quality': sum(quality_scores) / len(quality_scores) if quality_scores else None,
                'storage_path': str(self.storage_path),
                'max_memory_age_days': self.max_memory_age_days,
                'last_cleanup': datetime.now().isoformat()
            }
            
            return stats
    
    def _calculate_similarity(self, idea1: str, idea2: str) -> float:
        """Calculate similarity between two product ideas"""
        # Simple keyword-based similarity
        words1 = set(idea1.lower().split())
        words2 = set(idea2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _extract_relevant_insights(self, entry: MemoryEntry, current_idea: str) -> List[str]:
        """Extract relevant insights from a memory entry"""
        insights = []
        
        # Extract key features from previous output
        if 'plan' in entry.workflow_output:
            plan = entry.workflow_output['plan']
            if 'key_features_high_level' in plan:
                insights.extend([f"Previous features: {', '.join(plan['key_features_high_level'][:3])}"])
        
        # Extract target users
        if 'prd' in entry.workflow_output:
            prd = entry.workflow_output['prd']
            if 'target_users' in prd:
                insights.extend([f"Target users: {', '.join(prd['target_users'][:3])}"])
        
        # Extract tech stack
        if 'architecture' in entry.workflow_output:
            arch = entry.workflow_output['architecture']
            if 'tech_stack' in arch:
                tech_stack = list(arch['tech_stack'].keys())
                insights.extend([f"Tech stack: {', '.join(tech_stack[:3])}"])
        
        return insights[:3]  # Limit to top 3 insights
    
    def _generate_recommendations(self, context: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on context"""
        recommendations = []
        
        # Based on thread history
        if context['thread_history']:
            recommendations.append("Consider building on previous conversation context")
        
        # Based on similar ideas
        if context['similar_ideas']:
            recommendations.append("Leverage insights from similar product ideas")
        
        # Based on quality trends
        if context['thread_summary'] and context['thread_summary'].get('average_quality', 0) < 7.0:
            recommendations.append("Focus on improving output quality based on historical performance")
        
        return recommendations
    
    def _update_summary(self, thread_id: str):
        """Update conversation summary for a thread"""
        entries = self._entries[thread_id]
        
        if not entries:
            return
        
        # Calculate summary stats
        total_requests = len(entries)
        quality_scores = [entry.quality_score for entry in entries if entry.quality_score is not None]
        average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        # Extract topics and insights
        all_ideas = [entry.product_idea for entry in entries]
        topics = self._extract_topics(all_ideas)
        key_insights = self._extract_key_insights(entries)
        
        # Create or update summary
        summary = ConversationSummary(
            thread_id=thread_id,
            created_at=entries[0].timestamp,
            last_updated=entries[-1].timestamp,
            total_requests=total_requests,
            average_quality=average_quality,
            topics=topics,
            key_insights=key_insights
        )
        
        self._summaries[thread_id] = summary
    
    def _extract_topics(self, ideas: List[str]) -> List[str]:
        """Extract common topics from product ideas"""
        # Simple keyword extraction
        common_words = ['ai', 'app', 'tool', 'platform', 'system', 'management', 'automation']
        topics = []
        
        for word in common_words:
            if any(word in idea.lower() for idea in ideas):
                topics.append(word)
        
        return topics[:5]  # Limit to top 5 topics
    
    def _extract_key_insights(self, entries: List[MemoryEntry]) -> List[str]:
        """Extract key insights from conversation entries"""
        insights = []
        
        for entry in entries[-3:]:  # Last 3 entries
            if entry.quality_score and entry.quality_score > 8.0:
                insights.append(f"High-quality response: {entry.product_idea[:50]}...")
            
            if entry.improvements_made:
                insights.append(f"Improved output for: {entry.product_idea[:50]}...")
        
        return insights[:5]  # Limit to top 5 insights
    
    def _load_memory(self):
        """Load memory from disk"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load entries
                for thread_id, entry_dicts in data.get('entries', {}).items():
                    entries = [MemoryEntry.from_dict(entry_dict) for entry_dict in entry_dicts]
                    self._entries[thread_id] = entries
                
                # Load summaries
                for thread_id, summary_dict in data.get('summaries', {}).items():
                    summary = ConversationSummary(
                        thread_id=summary_dict['thread_id'],
                        created_at=datetime.fromisoformat(summary_dict['created_at']),
                        last_updated=datetime.fromisoformat(summary_dict['last_updated']),
                        total_requests=summary_dict['total_requests'],
                        average_quality=summary_dict.get('average_quality'),
                        topics=summary_dict.get('topics', []),
                        key_insights=summary_dict.get('key_insights', [])
                    )
                    self._summaries[thread_id] = summary
                
                logger.info(f"📂 Loaded {len(self._entries)} threads from memory")
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to load memory from disk: {str(e)}")
    
    def _save_memory(self):
        """Save memory to disk"""
        try:
            # Prepare data for saving
            data = {
                'entries': {
                    thread_id: [entry.to_dict() for entry in entries]
                    for thread_id, entries in self._entries.items()
                },
                'summaries': {
                    thread_id: asdict(summary)
                    for thread_id, summary in self._summaries.items()
                },
                'metadata': {
                    'saved_at': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 Saved memory to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save memory to disk: {str(e)}")
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)  # Run every hour
                    self.cleanup_old_entries()
                except Exception as e:
                    logger.error(f"❌ Cleanup thread error: {str(e)}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("🧹 Started memory cleanup thread")


# Global memory store instance
_memory_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get the global memory store instance"""
    global _memory_store
    
    if _memory_store is None:
        _memory_store = MemoryStore()
    
    return _memory_store


def create_memory_entry(thread_id: str, product_idea: str, workflow_output: Dict[str, Any], 
                       execution_time: float, quality_score: Optional[float] = None,
                       improvements_made: bool = False, metadata: Optional[Dict[str, Any]] = None) -> MemoryEntry:
    """Create a new memory entry"""
    return MemoryEntry(
        thread_id=thread_id,
        timestamp=datetime.now(),
        product_idea=product_idea,
        workflow_output=workflow_output,
        execution_time=execution_time,
        quality_score=quality_score,
        improvements_made=improvements_made,
        metadata=metadata
    )
