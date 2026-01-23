"""
Verification Handler
"""
import json
from utils import (
    UserDB,
    VerificationCodeDB,
    validate_verification_data,
    success_response,
    error_response,
    validation_error_response
)
from utils.schema_validator import validate_request_body
from utils.schemas import verification_schema

@validate_request_body(verification_schema)
def verify(event, context):
    """
    POST /auth/verify
    Verify email or SMS code
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validate input
        is_valid, errors = validate_verification_data(body)
        if not is_valid:
            return validation_error_response("Validation failed", errors)
        
        user_id = body['user_id']
        code = body['code']
        code_type = body['code_type']  # 'email' or 'sms'
        
        # Verify the code
        is_valid = VerificationCodeDB.verify_code(user_id, code_type, code)
        
        if not is_valid:
            return error_response("Invalid or expired verification code")
        
        # Get user
        user = UserDB.get_user_by_id(user_id)
        if not user:
            return error_response("User not found", status_code=404)
        
        # Update user verification status
        updates = {}
        
        if code_type == 'email':
            updates['email_verified'] = True
        elif code_type == 'sms':
            updates['phone_verified'] = True
        
        # Check if both email and phone are verified (if phone exists)
        if user.get('phone'):
            # User has phone, need both verifications
            email_verified = updates.get('email_verified', user.get('email_verified', False))
            phone_verified = updates.get('phone_verified', user.get('phone_verified', False))
            
            if email_verified and phone_verified:
                updates['is_verified'] = True
        else:
            # No phone, only need email verification
            if updates.get('email_verified'):
                updates['is_verified'] = True
        
        # Update user
        updated_user = UserDB.update_user(user_id, updates)
        
        return success_response(
            data={
                'user_id': user_id,
                'is_verified': updated_user.get('is_verified', False),
                'email_verified': updated_user.get('email_verified', False),
                'phone_verified': updated_user.get('phone_verified', False)
            },
            message=f"{code_type.capitalize()} verified successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Verification error: {str(e)}")
        return error_response("Verification failed", status_code=500)
