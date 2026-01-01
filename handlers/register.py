"""
Registration Handlers
"""
import uuid
import json
from datetime import datetime
from config import config, VALID_ROLES
from utils import (
    UserDB,
    VerificationCodeDB,
    hash_password,
    validate_registration_data,
    validate_role,
    success_response,
    error_response,
    validation_error_response,
    create_verification_record,
    send_email_verification,
    send_sms_verification
)
from middleware import register_rate_limit

@register_rate_limit()
def register(event, context):
    """
    POST /auth/register
    Register a new user
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validate input
        is_valid, errors = validate_registration_data(body)
        if not is_valid:
            return validation_error_response("Validation failed", errors)
        
    
        email = body['email'].lower().strip()
        password = body['password']
        first_name = body['first_name'].strip()
        last_name = body['last_name'].strip()
        phone = body.get('phone', '').strip()
        print(f"[LOG] User email: {email}")
        # Check if user already exists
        existing_user = UserDB.get_user_by_email(email)
        if existing_user:
            return error_response("Email already registered", status_code=409)
        
        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(password)
        
        user_data = {
            'user_id': user_id,
            'email': email,
            'password': hashed_password,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'role': 'customer',  # Default role for public registration (external user)
            'tenant_id': None,  # Customers are global users, not scoped to a tenant
            'is_verified': False,
            'is_locked': False,
            'failed_login_attempts': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        UserDB.create_user(user_data)
        
        # Generate and send verification codes
        # Email verification
        email_code_data = create_verification_record(user_id, 'email')
        VerificationCodeDB.create_code(email_code_data)
        send_email_verification(email, email_code_data['code'])
        
        # SMS verification (if phone provided)
        if phone:
            sms_code_data = create_verification_record(user_id, 'sms')
            VerificationCodeDB.create_code(sms_code_data)
            send_sms_verification(phone, sms_code_data['code'])
        
        # Return user data (without password)
        user_response = {
            'user_id': user_id,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'role': 'customer',
            'is_verified': False,
            'created_at': user_data['created_at']
        }
        
        return success_response(
            data=user_response,
            message="Registration successful. Please verify your email and phone.",
            status_code=201
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return error_response("Registration failed", status_code=500)


@register_rate_limit()
def register_master(event, context):
    """
    POST /auth/register-master
    Register a master user (requires secret key)
    """
    print("RAW EVENT BODY:", event)

    try:
        body = json.loads(event.get('body', '{}'))
        print(f"[LOG] Master registration: {body}")
        # Verify master secret key
        secret_key = body.get('secret_key')
        if not secret_key or secret_key != config.MASTER_SECRET_KEY:
            print("MMKK:", config.MASTER_SECRET_KEY)
            print("SK:", secret_key)    
            return error_response("Invalid master secret key", status_code=403)
            
        # Validate input
        is_valid, errors = validate_registration_data(body)
        if not is_valid:
            return validation_error_response("Validation failed", errors)
        
        email = body['email'].lower().strip()
        password = body['password']
        first_name = body['first_name'].strip()
        last_name = body['last_name'].strip()
        phone = body.get('phone', '').strip()
        
        # Check if user already exists
        existing_user = UserDB.get_user_by_email(email)
        if existing_user:
            return error_response("Email already registered", status_code=409)
        
        # Create master user
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(password)
        
        user_data = {
            'user_id': user_id,
            'email': email,
            'password': hashed_password,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'role': 'master',  # Master role
            'tenant_id': None,  # Master is a system role, not scoped to any tenant
            'is_verified': True,  # Auto-verify master users
            'is_locked': False,
            'failed_login_attempts': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        UserDB.create_user(user_data)
        
        # Return user data (without password)
        user_response = {
            'user_id': user_id,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'role': 'master',
            'is_verified': True,
            'created_at': user_data['created_at']
        }
        
        return success_response(
            data=user_response,
            message="Master user created successfully",
            status_code=201
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Master registration error: {str(e)}")
        return error_response("Master registration failed", status_code=500)
