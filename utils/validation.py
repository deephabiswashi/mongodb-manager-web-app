"""
Validation utilities for MongoDB operations
"""
import re
import json
from typing import Dict, Any, Tuple, Optional

# MongoDB naming rules
DB_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]{1,63}$')
COLLECTION_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]{1,255}$')
INVALID_DB_NAMES = {'admin', 'local', 'config', 'system'}


def validate_db_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate database name according to MongoDB rules.
    Returns (is_valid, error_message)
    """
    if not name or not isinstance(name, str):
        return False, "Database name must be a non-empty string"
    
    name = name.strip()
    if len(name) == 0:
        return False, "Database name cannot be empty"
    
    if len(name) > 63:
        return False, "Database name cannot exceed 63 characters"
    
    if name.lower() in INVALID_DB_NAMES:
        return False, f"Database name '{name}' is reserved and cannot be used"
    
    if not DB_NAME_PATTERN.match(name):
        return False, "Database name can only contain letters, numbers, underscores, and hyphens"
    
    if name.startswith('-') or name.startswith('_'):
        return False, "Database name cannot start with '-' or '_'"
    
    return True, None


def validate_collection_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate collection name according to MongoDB rules.
    Returns (is_valid, error_message)
    """
    if not name or not isinstance(name, str):
        return False, "Collection name must be a non-empty string"
    
    name = name.strip()
    if len(name) == 0:
        return False, "Collection name cannot be empty"
    
    if len(name) > 255:
        return False, "Collection name cannot exceed 255 characters"
    
    # MongoDB reserved collection prefixes
    if name.startswith('system.'):
        return False, "Collection name cannot start with 'system.'"
    
    if not COLLECTION_NAME_PATTERN.match(name):
        return False, "Collection name can only contain letters, numbers, underscores, hyphens, and dots"
    
    return True, None


def validate_json_payload(data: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate and parse JSON string.
    Returns (is_valid, parsed_data, error_message)
    """
    if not data or not isinstance(data, str):
        return False, None, "JSON must be a non-empty string"
    
    data = data.strip()
    if len(data) == 0:
        return False, None, "JSON cannot be empty"
    
    try:
        parsed = json.loads(data)
        if not isinstance(parsed, dict):
            return False, None, "JSON must be a valid object (dictionary)"
        return True, parsed, None
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON format: {str(e)}"


def validate_document_structure(doc: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate document structure for MongoDB insertion.
    Returns (is_valid, error_message)
    """
    if not isinstance(doc, dict):
        return False, "Document must be a dictionary"
    
    if len(doc) == 0:
        return False, "Document cannot be empty"
    
    # Check for top-level $ operators (which are not allowed at root)
    for key in doc.keys():
        if key.startswith('$') and key != '$oid' and key != '$date':
            return False, f"Invalid key '{key}': MongoDB operators are not allowed in document fields"
    
    return True, None


def sanitize_db_name(name: str) -> str:
    """
    Sanitize database name by removing invalid characters.
    Returns sanitized name.
    """
    if not name:
        return ""
    # Replace invalid chars with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    # Remove leading/trailing dashes/underscores
    sanitized = sanitized.strip('-_')
    # Limit length
    return sanitized[:63]


def sanitize_collection_name(name: str) -> str:
    """
    Sanitize collection name by removing invalid characters.
    Returns sanitized name.
    """
    if not name:
        return ""
    # Replace invalid chars with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    # Remove leading dots
    sanitized = sanitized.lstrip('.')
    # Limit length
    return sanitized[:255]

