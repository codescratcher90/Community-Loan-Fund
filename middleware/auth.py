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
    UserDB,
)


def require_auth(resource: Optional[str] = None, operation: Optional[str] = None):
    """
    Decorator to require authentication.

    No args:
        Validates JWT only. Use for self-service endpoints (profile, logout)
        where any authenticated user is allowed regardless of role.

    resource + operation:
        Validates JWT then checks DynamoDB resource permission.
        master always passes.
        No DB record for the resource/operation → denied (secure by default).

    Example:
        @require_auth()                                    # just needs login
        @require_auth(resource='users', operation='list')  # needs explicit grant
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

            if not (user.get('email_verified', False) or user.get('phone_verified', False)):
                return forbidden_response("Account is not verified")

            user_role = user.get('role', 'customer')

            if resource is not None and operation is not None:
                from utils.app_settings import has_resource_permission
                if not has_resource_permission(resource, operation, user_role):
                    return forbidden_response(
                        "You do not have permission to perform this action"
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
