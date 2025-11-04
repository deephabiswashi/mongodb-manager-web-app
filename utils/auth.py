"""
Authentication and authorization utilities
"""
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, Dict, Any, List
import re
from utils.mongo_utils import get_mongo_client
from utils.logger import app_logger


def get_auth_db(client, auth_db_name: str = "_auth"):
    """Get the authentication database"""
    return client[auth_db_name]


def create_default_user(client, auth_db_name: str = "_auth", username: str = "admin", password: str = "password"):
    """
    Create default admin user if it doesn't exist.
    Returns True if user was created, False if already exists.
    """
    auth_db = get_auth_db(client, auth_db_name)
    users_collection = auth_db["users"]
    
    # Check if user already exists
    if users_collection.find_one({"username": username}):
        app_logger.info(f"Default user '{username}' already exists")
        return False
    
    # Create default admin user
    hashed_password = generate_password_hash(password)
    # Backward-compat default admin (username-only). Also set email for new system.
    user_doc = {
        "username": username,
        "email": f"{username}@local",
        "password": hashed_password,
        "role": "admin",
        "permissions": {
            "databases": "*",  # Access to all databases
            "collections": "*",  # Access to all collections
            "can_create_db": True,
            "can_delete_db": False,
            "can_create_collection": True,
            "can_delete_collection": True,
            "can_import": True,
            "can_export": True
        },
        "created_at": None  # Will be set by MongoDB
    }
    
    result = users_collection.insert_one(user_doc)
    app_logger.info(f"Default admin user '{username}' created with ID: {result.inserted_id}")
    return True


def authenticate_user(client, username: str, password: str, auth_db_name: str = "_auth") -> Optional[Dict[str, Any]]:
    """
    Authenticate a user. Returns user document if successful, None otherwise.
    Excludes password from returned document.
    """
    auth_db = get_auth_db(client, auth_db_name)
    users_collection = auth_db["users"]
    
    user = users_collection.find_one({"username": username})
    if not user:
        app_logger.warning(f"Login attempt with non-existent username: {username}")
        return None
    
    # Verify password
    if not check_password_hash(user["password"], password):
        app_logger.warning(f"Failed login attempt for username: {username}")
        return None
    
    # Remove password from returned user object
    user.pop("password", None)
    user["_id"] = str(user["_id"])  # Convert ObjectId to string
    
    app_logger.info(f"User authenticated successfully: {username}")
    return user


# =========================
# Email-first auth (Phase 6.1)
# =========================
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def get_user_namespace(email: str) -> str:
    """Return a safe namespace prefix for a user's data (used in DB names)."""
    if not email:
        return "ns_default__"
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", email.lower())
    return f"ns_{safe}__"


def create_user_by_email(client, email: str, password: str, role: str = "user", 
                         permissions: Dict[str, Any] = None, auth_db_name: str = "_auth") -> bool:
    """Create a new user account identified by email. Returns True if created."""
    if not email or not EMAIL_REGEX.match(email):
        return False
    if not password or len(password) < 6:
        return False
    auth_db = get_auth_db(client, auth_db_name)
    users = auth_db["users"]
    if users.find_one({"email": email.lower()}):
        return False
    if permissions is None:
        permissions = {
            "databases": "*",  # we'll namespace-filter at runtime
            "collections": "*",
            "can_create_db": True,
            "can_delete_db": False,
            "can_create_collection": True,
            "can_delete_collection": True,
            "can_import": True,
            "can_export": True
        }
    hashed = generate_password_hash(password)
    doc = {
        "email": email.lower(),
        "password": hashed,
        "role": role,
        "permissions": permissions
    }
    users.insert_one(doc)
    app_logger.info(f"Created user by email: {email}")
    return True


def authenticate_user_by_email(client, email: str, password: str, auth_db_name: str = "_auth") -> Optional[Dict[str, Any]]:
    """Authenticate by email/password. Returns user doc without password on success."""
    if not email or not EMAIL_REGEX.match(email):
        return None
    auth_db = get_auth_db(client, auth_db_name)
    users = auth_db["users"]
    user = users.find_one({"email": email.lower()})
    if not user:
        return None
    if not check_password_hash(user["password"], password):
        return None
    user.pop("password", None)
    user["_id"] = str(user["_id"])
    return user


def get_user_by_username(client, username: str, auth_db_name: str = "_auth") -> Optional[Dict[str, Any]]:
    """Get user by username (without password)"""
    auth_db = get_auth_db(client, auth_db_name)
    users_collection = auth_db["users"]
    
    user = users_collection.find_one({"username": username})
    if not user:
        return None
    
    user.pop("password", None)
    user["_id"] = str(user["_id"])
    return user


def get_user_by_email(client, email: str, auth_db_name: str = "_auth") -> Optional[Dict[str, Any]]:
    auth_db = get_auth_db(client, auth_db_name)
    users = auth_db["users"]
    user = users.find_one({"email": (email or '').lower()})
    if not user:
        return None
    user.pop("password", None)
    user["_id"] = str(user["_id"])
    return user


def check_user_permission(user: Dict[str, Any], permission: str, resource: str = None) -> bool:
    """
    Check if user has permission for an action.
    Permission format: "can_create_db", "can_delete_collection", etc.
    Resource: database or collection name (optional)
    """
    if not user or "permissions" not in user:
        return False
    
    permissions = user.get("permissions", {})
    
    # Admins have all permissions
    if user.get("role") == "admin":
        return True
    
    # Check specific permission
    if permission.startswith("can_"):
        return permissions.get(permission, False)
    
    # Check database/collection access
    if resource:
        db_access = permissions.get("databases", [])
        if db_access == "*":
            return True
        if isinstance(db_access, list) and resource in db_access:
            return True
    
    return False


def get_user_databases(client, user: Dict[str, Any], auth_db_name: str = "_auth") -> List[str]:
    """
    Get list of databases user has access to.
    Returns list of database names.
    """
    from utils.mongo_utils import list_databases
    
    all_databases = list_databases(client)
    permissions = user.get("permissions", {})
    db_access = permissions.get("databases", [])
    
    # Namespace isolation: regular users only see DBs with their namespace prefix
    if user.get("role") == "admin":
        return all_databases
    ns = get_user_namespace(user.get("email") or user.get("username"))
    filtered = [db for db in all_databases if db.startswith(ns)]
    return filtered
    
    # (Optional) If you want explicit allow-list instead of namespace, uncomment:
    # if isinstance(db_access, list):
    #     return [db for db in all_databases if db in db_access]
    # return []


def create_user(client, username: str, password: str, role: str = "user", 
                permissions: Dict[str, Any] = None, auth_db_name: str = "_auth") -> bool:
    """
    Create a new user. Returns True if created, False if username exists.
    """
    auth_db = get_auth_db(client, auth_db_name)
    users_collection = auth_db["users"]
    
    # Check if username exists
    if users_collection.find_one({"username": username}):
        app_logger.warning(f"Attempt to create duplicate username: {username}")
        return False
    
    # Default permissions for regular users
    if permissions is None:
        permissions = {
            "databases": [],
            "collections": "*",
            "can_create_db": False,
            "can_delete_db": False,
            "can_create_collection": True,
            "can_delete_collection": False,
            "can_import": True,
            "can_export": True
        }
    
    hashed_password = generate_password_hash(password)
    user_doc = {
        "username": username,
        "password": hashed_password,
        "role": role,
        "permissions": permissions
    }
    
    result = users_collection.insert_one(user_doc)
    app_logger.info(f"New user created: {username} (role: {role})")
    return True

