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
from config import has_permission
from config.permissions import can_perform


def require_auth(required_role: Optional[str] = None, action: Optional[str] = None):
    """
    Decorator to require authentication.

    Two ways to specify what permission is needed (pick one):
      required_role='admin'        — legacy: user must be at least this role level
      action='list_users'          — preferred: user must have this named action

    Using action= is preferred for new handlers because it decouples
    the permission check from the role hierarchy and makes the matrix
    in config/permissions.py the single source of truth.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(event, context):
            auth_header = (
                event.get('headers', {}).get('Authorization') or
                event.get('headers', {}).get('authorization')
            )

            token = extract_token_from_header(auth_header)
            if not token:
                return unauthorized_response("Missing or invalid authorization token")

            payload = verify_access_token(token)
            if not payload:
                return unauthorized_response("Invalid or expired token")

            user = UserDB.get_user_by_id(payload['user_id'])
            if not user:
                return unauthorized_response("User not found")

            if user.get('is_locked', False):
                return forbidden_response("Account is locked")

            if not user.get('is_verified', False):
                return forbidden_response("Account is not verified")

            user_role = user.get('role', 'customer')

            # Action-based check (preferred)
            if action is not None:
                if not can_perform(user_role, action):
                    return forbidden_response(
                        f"You do not have permission to perform this action"
                    )

            # Legacy hierarchy check
            elif required_role is not None:
                if not has_permission(user_role, required_role):
                    return forbidden_response(
                        f"Insufficient permissions. Required role: {required_role}"
                    )

            event['user'] = {
                'user_id':   payload['user_id'],
                'email':     payload['email'],
                'role':      user_role,
                'tenant_id': user.get('tenant_id'),
            }

            return func(event, context)

        return wrapper
    return decorator


def get_current_user(event: dict) -> Optional[dict]:
    """Return the authenticated user attached to the event, or None."""
    return event.get('user')
