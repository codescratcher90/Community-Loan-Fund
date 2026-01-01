"""
User Management Handlers (Admin/Master)
"""
import json
import uuid
from datetime import datetime
from config import can_modify_role, is_internal_role, is_external_role, requires_tenant
from utils import (
    UserDB,
    validate_role,
    validate_registration_data,
    hash_password,
    success_response,
    error_response,
    not_found_response,
    forbidden_response,
    validation_error_response
)
from middleware import require_auth, get_current_user

@require_auth(required_role='admin')
def list_users(event, context):
    """
    GET /users
    List all users (admin+)
    - Master: sees all users across all tenants
    - Internal users (owner, admin, etc.): see only users in their tenant
    """
    try:
        current_user = get_current_user(event)

        # Get query parameters for pagination (optional)
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 100))

        # Get users based on role and tenant
        if current_user['role'] == 'master':
            # Master sees all users
            users = UserDB.list_users(limit=limit)
        else:
            # Internal users see only users in their tenant
            tenant_id = current_user.get('tenant_id')
            if not tenant_id:
                return error_response("User has no tenant association", status_code=400)
            users = UserDB.list_users(limit=limit, tenant_id=tenant_id)

        # Remove sensitive data
        users_response = []
        for user in users:
            users_response.append({
                'user_id': user['user_id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'phone': user.get('phone', ''),
                'role': user['role'],
                'tenant_id': user.get('tenant_id'),
                'is_verified': user.get('is_verified', False),
                'is_locked': user.get('is_locked', False),
                'created_at': user.get('created_at')
            })

        return success_response(
            data={
                'users': users_response,
                'count': len(users_response)
            }
        )

    except Exception as e:
        print(f"List users error: {str(e)}")
        return error_response("Failed to list users", status_code=500)


@require_auth(required_role='admin')
def get_user(event, context):
    """
    GET /users/:id
    Get specific user (admin+)
    - Master: can view any user
    - Internal users: can only view users in their tenant
    """
    try:
        current_user = get_current_user(event)
        user_id = event['pathParameters']['id']

        # Get user
        user = UserDB.get_user_by_id(user_id)

        if not user:
            return not_found_response("User not found")

        # Check tenant access (unless master)
        if current_user['role'] != 'master':
            current_tenant_id = current_user.get('tenant_id')
            target_tenant_id = user.get('tenant_id')

            # Internal users can only view users in their tenant
            if current_tenant_id != target_tenant_id:
                return forbidden_response("You don't have permission to view this user")

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
            'email_verified': user.get('email_verified', False),
            'phone_verified': user.get('phone_verified', False),
            'failed_login_attempts': user.get('failed_login_attempts', 0),
            'created_at': user.get('created_at'),
            'updated_at': user.get('updated_at')
        }

        return success_response(data=user_response)

    except Exception as e:
        print(f"Get user error: {str(e)}")
        return error_response("Failed to get user", status_code=500)


@require_auth(required_role='admin')
def update_user_role(event, context):
    """
    PUT /users/:id/role
    Update user role (admin/master)
    - Master: can modify any user's role
    - Internal users: can only modify users in their tenant
    - Changing to internal role assigns user to modifier's tenant
    - Changing to external role (customer) removes tenant association
    """
    try:
        from config import is_internal_role, is_external_role

        current_user = get_current_user(event)
        user_id = event['pathParameters']['id']
        body = json.loads(event.get('body', '{}'))

        new_role = body.get('role')

        # Validate role
        is_valid, error = validate_role(new_role)
        if not is_valid:
            return validation_error_response(error)

        # Get target user
        target_user = UserDB.get_user_by_id(user_id)
        if not target_user:
            return not_found_response("User not found")

        # Check tenant access (unless master)
        if current_user['role'] != 'master':
            current_tenant_id = current_user.get('tenant_id')
            target_tenant_id = target_user.get('tenant_id')

            # Internal users can only modify users in their tenant
            if target_tenant_id and current_tenant_id != target_tenant_id:
                return forbidden_response("You don't have permission to modify this user")

        # Check if current user can modify target user's role
        can_modify = can_modify_role(
            current_user['role'],
            target_user['role'],
            new_role
        )

        if not can_modify:
            return forbidden_response(
                "You don't have permission to change this user's role to the specified role"
            )

        # Prepare updates
        updates = {
            'role': new_role,
            'updated_at': datetime.utcnow().isoformat()
        }

        # Handle tenant_id based on new role
        if is_internal_role(new_role):
            # Promoting to internal role - assign to modifier's tenant (or keep existing for master)
            if current_user['role'] == 'master':
                # Master can specify tenant_id in request, or leave it as is
                new_tenant_id = body.get('tenant_id', target_user.get('tenant_id'))
                updates['tenant_id'] = new_tenant_id
            else:
                # Internal users assign to their own tenant
                updates['tenant_id'] = current_user.get('tenant_id')
        elif is_external_role(new_role):
            # Demoting to customer - remove tenant association
            updates['tenant_id'] = None

        updated_user = UserDB.update_user(user_id, updates)

        return success_response(
            data={
                'user_id': updated_user['user_id'],
                'email': updated_user['email'],
                'role': updated_user['role'],
                'tenant_id': updated_user.get('tenant_id'),
                'updated_at': updated_user['updated_at']
            },
            message=f"User role updated to {new_role}"
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Update role error: {str(e)}")
        return error_response("Failed to update user role", status_code=500)


@require_auth(required_role='master')
def delete_user(event, context):
    """
    DELETE /users/:id
    Delete user (master only)
    - Master can delete any user
    """
    try:
        current_user = get_current_user(event)
        user_id = event['pathParameters']['id']

        # Prevent self-deletion
        if user_id == current_user['user_id']:
            return error_response("Cannot delete your own account")

        # Get target user
        target_user = UserDB.get_user_by_id(user_id)
        if not target_user:
            return not_found_response("User not found")

        # Delete user
        UserDB.delete_user(user_id)

        # Also delete associated refresh tokens
        from utils import RefreshTokenDB
        RefreshTokenDB.delete_user_tokens(user_id)

        return success_response(
            message="User deleted successfully"
        )

    except Exception as e:
        print(f"Delete user error: {str(e)}")
        return error_response("Failed to delete user", status_code=500)


@require_auth(required_role='admin')
def create_internal_user(event, context):
    """
    POST /users
    Create a new internal user (owner, admin, staff, etc.)
    - Master: can create owners with new tenant_id or internal users with specified tenant_id
    - Owners/Admins: can create internal users within their own tenant only
    """
    try:
        current_user = get_current_user(event)
        body = json.loads(event.get('body', '{}'))

        # Validate basic registration data
        is_valid, errors = validate_registration_data(body)
        if not is_valid:
            return validation_error_response("Validation failed", errors)

        email = body['email'].lower().strip()
        password = body['password']
        first_name = body['first_name'].strip()
        last_name = body['last_name'].strip()
        phone = body.get('phone', '').strip()
        role = body.get('role', 'staff')  # Default to staff for internal users

        # Validate role
        is_valid_role, role_error = validate_role(role)
        if not is_valid_role:
            return validation_error_response(role_error)

        # Determine tenant_id based on current user and target role
        if current_user['role'] == 'master':
            # Master can specify tenant_id for creating owners or internal users
            if role == 'owner':
                # Creating a new owner - generate new tenant_id
                tenant_id = body.get('tenant_id', str(uuid.uuid4()))
            elif is_internal_role(role):
                # Creating internal user - must specify tenant_id
                tenant_id = body.get('tenant_id')
                if not tenant_id:
                    return validation_error_response("tenant_id is required when creating internal users")
            else:
                # Creating customer - no tenant
                tenant_id = None
        else:
            # Internal users can only create users within their own tenant
            if is_external_role(role):
                return forbidden_response("You cannot create external users (customers)")

            if role == 'owner':
                return forbidden_response("Only master can create owners")

            # Check if they can create this role
            if not can_modify_role(current_user['role'], 'customer', role):
                return forbidden_response(f"You don't have permission to create users with role: {role}")

            # Assign to current user's tenant
            tenant_id = current_user.get('tenant_id')
            if not tenant_id:
                return error_response("User has no tenant association", status_code=400)

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
            'role': role,
            'tenant_id': tenant_id,
            'is_verified': True,  # Internal users are auto-verified
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
            'role': role,
            'tenant_id': tenant_id,
            'is_verified': True,
            'created_at': user_data['created_at']
        }

        return success_response(
            data=user_response,
            message=f"{role.capitalize()} user created successfully",
            status_code=201
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Create internal user error: {str(e)}")
        return error_response("Failed to create user", status_code=500)
