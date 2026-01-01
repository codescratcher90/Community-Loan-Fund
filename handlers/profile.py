"""
User Profile Handlers
"""
import json
from datetime import datetime
from utils import (
    UserDB,
    hash_password,
    validate_password,
    validate_name,
    validate_phone,
    success_response,
    error_response,
    validation_error_response
)
from middleware import require_auth, get_current_user

@require_auth()
def get_me(event, context):
    """
    GET /auth/me
    Get current user profile
    """
    try:
        current_user = get_current_user(event)
        
        # Get full user data
        user = UserDB.get_user_by_id(current_user['user_id'])
        
        if not user:
            return error_response("User not found", status_code=404)
        
        # Remove sensitive data
        user_response = {
            'user_id': user['user_id'],
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'phone': user.get('phone', ''),
            'role': user['role'],
            'tenant_id': user.get('tenant_id'),
            'is_verified': user.get('is_verified', False),
            'is_locked': user.get('is_locked', False),
            'created_at': user.get('created_at'),
            'updated_at': user.get('updated_at')
        }
        
        return success_response(data=user_response)
        
    except Exception as e:
        print(f"Get profile error: {str(e)}")
        return error_response("Failed to get profile", status_code=500)


@require_auth()
def update_me(event, context):
    """
    PUT /auth/me
    Update current user profile
    """
    try:
        current_user = get_current_user(event)
        body = json.loads(event.get('body', '{}'))
        
        # Get current user data
        user = UserDB.get_user_by_id(current_user['user_id'])
        if not user:
            return error_response("User not found", status_code=404)
        
        # Validate and collect updates
        updates = {}
        errors = {}
        
        # First name
        if 'first_name' in body:
            is_valid, error = validate_name(body['first_name'], "First name")
            if is_valid:
                updates['first_name'] = body['first_name'].strip()
            else:
                errors['first_name'] = error
        
        # Last name
        if 'last_name' in body:
            is_valid, error = validate_name(body['last_name'], "Last name")
            if is_valid:
                updates['last_name'] = body['last_name'].strip()
            else:
                errors['last_name'] = error
        
        # Phone
        if 'phone' in body:
            is_valid, error = validate_phone(body['phone'])
            if is_valid:
                updates['phone'] = body['phone'].strip()
            else:
                errors['phone'] = error
        
        # Password (if changing)
        if 'password' in body:
            is_valid, error = validate_password(body['password'])
            if is_valid:
                # Require current password for password change
                if 'current_password' not in body:
                    errors['current_password'] = "Current password is required to change password"
                else:
                    from utils import verify_password
                    if not verify_password(body['current_password'], user['password']):
                        errors['current_password'] = "Current password is incorrect"
                    else:
                        updates['password'] = hash_password(body['password'])
            else:
                errors['password'] = error
        
        if errors:
            return validation_error_response("Validation failed", errors)
        
        if not updates:
            return error_response("No valid fields to update")
        
        # Add updated timestamp
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        # Update user
        updated_user = UserDB.update_user(current_user['user_id'], updates)
        
        # Remove sensitive data
        user_response = {
            'user_id': updated_user['user_id'],
            'email': updated_user['email'],
            'first_name': updated_user['first_name'],
            'last_name': updated_user['last_name'],
            'phone': updated_user.get('phone', ''),
            'role': updated_user['role'],
            'tenant_id': updated_user.get('tenant_id'),
            'updated_at': updated_user['updated_at']
        }
        
        return success_response(
            data=user_response,
            message="Profile updated successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Update profile error: {str(e)}")
        return error_response("Failed to update profile", status_code=500)
