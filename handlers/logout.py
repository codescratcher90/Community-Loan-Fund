"""
Logout Handler
"""
import json
from utils import (
    RefreshTokenDB,
    success_response,
    error_response
)
from utils.schema_validator import validate_request_body
from utils.schemas import logout_schema
from middleware import require_auth

@require_auth()
@validate_request_body(logout_schema)
def logout(event, context):
    """
    POST /auth/logout
    Logout user (revoke refresh token)
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        refresh_token = body.get('refresh_token')
        
        if not refresh_token:
            return error_response("Refresh token is required")
        
        # Delete refresh token
        RefreshTokenDB.delete_token(refresh_token)
        
        return success_response(
            message="Logged out successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return error_response("Logout failed", status_code=500)
