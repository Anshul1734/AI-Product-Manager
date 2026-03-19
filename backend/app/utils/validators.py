"""
Validation utility functions.
"""
import re
from typing import Optional


def validate_product_idea(idea: str) -> tuple[bool, list[str]]:
    """Validate product idea and return (is_valid, errors)."""
    errors = []
    
    if not idea or not idea.strip():
        errors.append("Product idea cannot be empty")
        return False, errors
    
    idea = idea.strip()
    
    # Length validation
    if len(idea) < 10:
        errors.append("Product idea must be at least 10 characters long")
    
    if len(idea) > 2000:
        errors.append("Product idea cannot exceed 2000 characters")
    
    # Content validation
    if not re.search(r'[a-zA-Z]', idea):
        errors.append("Product idea must contain at least one letter")
    
    # Check for potentially harmful content
    harmful_patterns = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload=',
        r'onerror=',
        r'onclick='
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, idea, re.IGNORECASE):
            errors.append("Product idea contains potentially harmful content")
            break
    
    return len(errors) == 0, errors


def validate_thread_id(thread_id: Optional[str]) -> tuple[bool, list[str]]:
    """Validate thread ID and return (is_valid, errors)."""
    errors = []
    
    if not thread_id:
        # Thread ID is optional
        return True, errors
    
    if not isinstance(thread_id, str):
        errors.append("Thread ID must be a string")
        return False, errors
    
    thread_id = thread_id.strip()
    
    if not thread_id:
        return True, errors  # Empty string is valid (no thread)
    
    # Length validation
    if len(thread_id) > 255:
        errors.append("Thread ID cannot exceed 255 characters")
    
    # Format validation (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', thread_id):
        errors.append("Thread ID can only contain letters, numbers, hyphens, and underscores")
    
    return len(errors) == 0, errors


def validate_export_type(export_type: str) -> tuple[bool, list[str]]:
    """Validate export type and return (is_valid, errors)."""
    errors = []
    
    valid_types = ['pdf', 'csv', 'json']
    
    if not export_type:
        errors.append("Export type is required")
        return False, errors
    
    if export_type.lower() not in valid_types:
        errors.append(f"Export type must be one of: {', '.join(valid_types)}")
    
    return len(errors) == 0, errors


def validate_pagination_params(limit: int, offset: int) -> tuple[bool, list[str]]:
    """Validate pagination parameters."""
    errors = []
    
    if limit < 1:
        errors.append("Limit must be at least 1")
    elif limit > 100:
        errors.append("Limit cannot exceed 100")
    
    if offset < 0:
        errors.append("Offset cannot be negative")
    
    return len(errors) == 0, errors
