"""
Authentication Middleware
"""
from functools import wraps
from typing import Callable, Optional
from utils import (
    verify_access_token,
    extract_token_from_header,
    unauthorized_response,
    forbidden_response,
    UserDB
)
from config import has_permission, PERMISSIONS

def require_auth(required_role: Optional[str] = None):
    """
    Decorator to require authentication
    If required_role is specified, also checks role permission
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(event, context):
            # Extract token from Authorization header
            auth_header = event.get('headers', {}).get('Authorization') or \
                         event.get('headers', {}).get('authorization')
            
            token = extract_token_from_header(auth_header)
            
            if not token:
                return unauthorized_response("Missing or invalid authorization token")
            
            # Verify token
            payload = verify_access_token(token)
            
            if not payload:
                return unauthorized_response("Invalid or expired token")
            
            # Get user from database to ensure they still exist and aren't locked
            user = UserDB.get_user_by_id(payload['user_id'])
            
            if not user:
                return unauthorized_response("User not found")
            
            if user.get('is_locked', False):
                return forbidden_response("Account is locked")
            
            if not user.get('is_verified', False):
                return forbidden_response("Account is not verified")
            
            # Check role permission if required
            if required_role:
                user_role = user.get('role', 'user')
                if not has_permission(user_role, required_role):
                    return forbidden_response(
                        f"Insufficient permissions. Required role: {required_role}"
                    )
            
            # Add user info to event for use in handler
            event['user'] = {
                'user_id': payload['user_id'],
                'email': payload['email'],
                'role': payload['role'],
                'tenant_id': user.get('tenant_id')  # Include tenant_id for multi-tenant access control
            }
            
            return func(event, context)
        
        return wrapper
    return decorator


def get_current_user(event: dict) -> Optional[dict]:
    """
    Get current authenticated user from event
    Returns user dict if authenticated, None otherwise
    """
    return event.get('user')


def check_endpoint_permission(method: str, path: str, user_role: str) -> bool:
    """
    Check if user has permission to access endpoint
    """
    # Normalize path for dynamic segments
    normalized_path = path
    
    # Replace dynamic segments with :id pattern
    import re
    normalized_path = re.sub(r'/[a-zA-Z0-9_-]+/', '/:id/', normalized_path)
    
    endpoint_key = f"{method}:{normalized_path}"
    required_role = PERMISSIONS.get(endpoint_key)
    
    # If endpoint not in permissions config, require authentication
    if required_role is None and endpoint_key not in PERMISSIONS:
        required_role = 'user'
    
    return has_permission(user_role, required_role) if required_role else True
