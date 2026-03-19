"""
Helper utility functions.
"""
import uuid
import re
from typing import Union


def sanitize_string(text: str, max_length: int = 200) -> str:
    """Sanitize string for logging and display."""
    if not text:
        return ""
    
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', text)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized.strip()


def generate_uuid() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def format_execution_time(seconds: Union[float, int]) -> str:
    """Format execution time in human-readable format."""
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.2f}s"


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string with ellipsis."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."


def extract_keywords(text: str, max_keywords: int = 10) -> list:
    """Extract keywords from text."""
    if not text:
        return []
    
    # Simple keyword extraction - in production, use NLP libraries
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter out common words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'}
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Return most common keywords
    from collections import Counter
    keyword_counts = Counter(keywords)
    
    return [word for word, count in keyword_counts.most_common(max_keywords)]
