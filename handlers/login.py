"""
Login Handler
"""
import json
from datetime import datetime
from config import config
from utils import (
    UserDB,
    RefreshTokenDB,
    LoginAttemptDB,
    verify_password,
    generate_access_token,
    generate_refresh_token,
    validate_login_data,
    success_response,
    error_response,
    validation_error_response
)
from decimal import Decimal

from middleware import login_rate_limit

@login_rate_limit()
def login(event, context):
    """
    POST /auth/login
    User login
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validate input
        is_valid, errors = validate_login_data(body)
        if not is_valid:
            return validation_error_response("Validation failed", errors)
        
        email = body['email'].lower().strip()
        password = body['password']
        
        # Get IP address
        ip_address = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
        
        # Get user
        user = UserDB.get_user_by_email(email)
        
        if not user:
            # Record failed attempt
            LoginAttemptDB.record_attempt(ip_address, email, success=False)
            return error_response("Invalid email or password", status_code=401)
        
        # Check if account is locked
        if user.get('is_locked', False):
            return error_response("Account is locked due to too many failed login attempts", status_code=403)
        
        # Check if account is verified
        if not user.get('is_verified', False):
            return error_response("Account is not verified. Please verify your email and phone.", status_code=403)
        
        # Verify password
        if not verify_password(password, user['password']):
            # Increment failed attempts
            failed_attempts = UserDB.increment_failed_attempts(user['user_id'])
            
            # Lock account if too many failed attempts
            if failed_attempts >= config.MAX_FAILED_LOGIN_ATTEMPTS:
                UserDB.lock_account(user['user_id'])
                return error_response(
                    f"Account locked due to {config.MAX_FAILED_LOGIN_ATTEMPTS} failed login attempts",
                    status_code=403
                )
            
            # Record failed attempt
            LoginAttemptDB.record_attempt(ip_address, email, success=False)
            
            remaining_attempts = config.MAX_FAILED_LOGIN_ATTEMPTS - failed_attempts
            return error_response(
                f"Invalid email or password. {remaining_attempts} attempts remaining.",
                status_code=401
            )
        
        # Successful login - reset failed attempts
        UserDB.reset_failed_attempts(user['user_id'])
        
        # Record successful attempt
        LoginAttemptDB.record_attempt(ip_address, email, success=True)
        
        # Generate tokens
        access_token = generate_access_token(
            user['user_id'],
            user['email'],
            user['role']
        )

        refresh_token = generate_refresh_token(user['user_id'])

        # Store refresh token
        current_timestamp = datetime.utcnow().timestamp()
        expires_at_timestamp = int(current_timestamp + config.REFRESH_TOKEN_EXPIRY)

        refresh_token_data = {
            'token': refresh_token,
            'user_id': user['user_id'],
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': Decimal(str(expires_at_timestamp))
        }
        RefreshTokenDB.create_token(refresh_token_data)

        # Calculate access token expiration
        access_expires_at = int(current_timestamp + config.ACCESS_TOKEN_EXPIRY)

        # Return unified response with separate user and tokens sections
        return success_response(
            data={
                'user': {
                    'user_id': user['user_id'],
                    'email': user['email'],
                    'first_name': user.get('first_name'),
                    'last_name': user.get('last_name'),
                    'role': user['role']
                },
                'tokens': {
                    'access': access_token,
                    'refresh': refresh_token,
                    'type': 'Bearer',
                    'expires_in': config.ACCESS_TOKEN_EXPIRY,
                    'expires_at': access_expires_at
                }
            },
            message="Login successful",
            status_code=200
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Login error: {str(e)}")
        return error_response("Login failed", status_code=500)
