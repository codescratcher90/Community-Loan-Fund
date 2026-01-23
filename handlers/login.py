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
    login_success_response,
    error_response,
    validation_error_response,
    get_setting
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

        # Get settings
        max_failed_login_attempts = get_setting('max_failed_login_attempts', 5)
        account_lockout_duration_minutes = get_setting('account_lockout_duration_minutes', 30)
        email_verification_required = get_setting('email_verification_required', True)

        # Check if account should be auto-unlocked
        if user.get('is_locked', False):
            if UserDB.should_auto_unlock(user, account_lockout_duration_minutes):
                # Auto-unlock the account
                UserDB.unlock_account(user['user_id'])
                print(f"[INFO] Auto-unlocked account for user {user['user_id']}")
                user['is_locked'] = False
                user['failed_login_attempts'] = 0
            else:
                # Account is still locked
                if account_lockout_duration_minutes == 0:
                    return error_response("Account is permanently locked. Contact support.", status_code=403)
                else:
                    return error_response(
                        f"Account is locked due to too many failed login attempts. Try again later.",
                        status_code=403
                    )
        
        # Check if account is verified (only if email verification is required)
        if email_verification_required and not user.get('is_verified', False):
            return error_response("Account is not verified. Please verify your email and phone.", status_code=403)
        
        # Verify password
        if not verify_password(password, user['password']):
            # Increment failed attempts
            failed_attempts = UserDB.increment_failed_attempts(user['user_id'])

            # Lock account if too many failed attempts
            if failed_attempts >= max_failed_login_attempts:
                UserDB.lock_account(user['user_id'])

                if account_lockout_duration_minutes == 0:
                    return error_response(
                        f"Account permanently locked due to {max_failed_login_attempts} failed login attempts. Contact support.",
                        status_code=403
                    )
                else:
                    return error_response(
                        f"Account locked for {account_lockout_duration_minutes} minutes due to {max_failed_login_attempts} failed login attempts",
                        status_code=403
                    )

            # Record failed attempt
            LoginAttemptDB.record_attempt(ip_address, email, success=False)

            remaining_attempts = max_failed_login_attempts - failed_attempts
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

        # Return login success response
        return login_success_response(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=config.ACCESS_TOKEN_EXPIRY
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Login error: {str(e)}")
        return error_response("Login failed", status_code=500)
