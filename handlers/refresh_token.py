"""
Token Refresh Handler
"""
import json
from datetime import datetime
from config import config
from utils import (
    UserDB,
    RefreshTokenDB,
    verify_refresh_token,
    generate_access_token,
    generate_refresh_token,
    success_response,
    error_response,
    unauthorized_response
)
from utils.schema_validator import validate_request_body
from utils.schemas import refresh_token_schema

@validate_request_body(refresh_token_schema)
def refresh(event, context):
    """
    POST /auth/refresh
    Refresh access token using refresh token
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        refresh_token = body.get('refresh_token')
        
        if not refresh_token:
            return error_response("Refresh token is required")
        
        # Verify refresh token
        payload = verify_refresh_token(refresh_token)
        
        if not payload:
            return unauthorized_response("Invalid or expired refresh token")
        
        # Check if token exists in database
        stored_token = RefreshTokenDB.get_token(refresh_token)
        
        if not stored_token:
            return unauthorized_response("Refresh token not found or has been revoked")
        
        # Get user
        user = UserDB.get_user_by_id(payload['user_id'])
        
        if not user:
            return unauthorized_response("User not found")
        
        # Check if account is locked
        if user.get('is_locked', False):
            return error_response("Account is locked", status_code=403)
        
        # Check if account is verified
        if not user.get('is_verified', False):
            return error_response("Account is not verified", status_code=403)
        
        # Generate new access token
        new_access_token = generate_access_token(
            user['user_id'],
            user['email'],
            user['role']
        )
        
        # Optionally: Generate new refresh token (token rotation)
        # For now, we'll keep the same refresh token
        
        return success_response(
            data={
                'access_token': new_access_token,
                'token_type': 'Bearer',
                'expires_in': config.ACCESS_TOKEN_EXPIRY
            },
            message="Token refreshed successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        return error_response("Token refresh failed", status_code=500)
