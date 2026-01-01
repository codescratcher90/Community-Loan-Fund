"""
Role-based Access Control Configuration
Multi-tenant RBAC system with internal (tenant-scoped) and external (global) roles.
"""

# Role hierarchy (higher number = more privileges)
ROLE_HIERARCHY = {
    'master': 8,        # System developer - god mode, no tenant
    'owner': 7,         # Tenant owner - manages their organization
    'admin': 6,         # Tenant administrator
    'manager': 5,       # Tenant manager
    'supervisor': 4,    # Tenant supervisor
    'coordinator': 3,   # Tenant coordinator
    'staff': 2,         # Tenant staff member
    'customer': 1       # External user - global, no tenant
}

# Valid roles list
VALID_ROLES = list(ROLE_HIERARCHY.keys())

# Internal roles (scoped to specific tenant)
INTERNAL_ROLES = ['owner', 'admin', 'manager', 'supervisor', 'coordinator', 'staff']

# External roles (global users, not scoped to tenant)
EXTERNAL_ROLES = ['customer']

# System roles (special privileges)
SYSTEM_ROLES = ['master']

# Permissions mapping: endpoint -> minimum required role
PERMISSIONS = {
    # Auth endpoints (public)
    'POST:/auth/register': None,
    'POST:/auth/register-master': None,  # Requires secret key
    'POST:/auth/verify': None,
    'POST:/auth/login': None,
    'POST:/auth/refresh': None,
    
    # Auth endpoints (authenticated)
    'POST:/auth/logout': 'customer',  # Any authenticated user
    'GET:/auth/me': 'customer',
    'PUT:/auth/me': 'customer',

    # User management endpoints
    'GET:/users': 'admin',  # List all users (admin can see tenant users, master sees all)
    'POST:/users': 'admin',  # Create internal user (admin creates in their tenant, master anywhere)
    'GET:/users/:id': 'admin',  # Get specific user
    'PUT:/users/:id/role': 'admin',  # Change user role
    'DELETE:/users/:id': 'master',  # Delete user (master only)
}

def has_permission(user_role: str, required_role: str) -> bool:
    """
    Check if user_role has permission for required_role
    Returns True if user_role is equal to or higher than required_role
    """
    if required_role is None:
        return True
    
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    
    return user_level >= required_level

def can_modify_role(modifier_role: str, target_role: str, new_role: str) -> bool:
    """
    Check if modifier can change target's role to new_role
    Rules:
    - Master can modify anyone
    - Owner/Admin can modify anyone in their tenant except those at or above their level
    - Cannot promote someone to a role higher than or equal to your own
    """
    modifier_level = ROLE_HIERARCHY.get(modifier_role, 0)
    target_level = ROLE_HIERARCHY.get(target_role, 0)
    new_level = ROLE_HIERARCHY.get(new_role, 0)

    # Master can do anything
    if modifier_role == 'master':
        return True

    # Cannot modify master users
    if target_role == 'master':
        return False

    # Cannot promote to master (only master can do that)
    if new_role == 'master':
        return False

    # Can only modify users below your level
    if target_level >= modifier_level:
        return False

    # Cannot promote to your level or higher
    if new_level >= modifier_level:
        return False

    return True

def is_internal_role(role: str) -> bool:
    """
    Check if role is an internal (tenant-scoped) role
    """
    return role in INTERNAL_ROLES

def is_external_role(role: str) -> bool:
    """
    Check if role is an external (global) role
    """
    return role in EXTERNAL_ROLES

def is_system_role(role: str) -> bool:
    """
    Check if role is a system role
    """
    return role in SYSTEM_ROLES

def requires_tenant(role: str) -> bool:
    """
    Check if a role requires tenant_id to be set
    """
    return is_internal_role(role)

def check_tenant_access(user_role: str, user_tenant_id: str, resource_tenant_id: str, resource_owner_id: str = None, user_id: str = None) -> bool:
    """
    Check if user has access to a resource based on tenant isolation rules

    Args:
        user_role: The user's role
        user_tenant_id: The user's tenant_id (None for master/customer)
        resource_tenant_id: The resource's tenant_id
        resource_owner_id: The resource owner's user_id (for customer-owned resources)
        user_id: The current user's ID (for checking ownership)

    Returns:
        True if user has access, False otherwise

    Rules:
        - Master: can access everything
        - Internal users (owner, admin, staff, etc.): can only access resources in their tenant
        - Customers: can only access their own resources (across all tenants)
    """
    # Master can access everything
    if user_role == 'master':
        return True

    # Customer can only access their own resources
    if is_external_role(user_role):
        if resource_owner_id and user_id:
            return resource_owner_id == user_id
        return False

    # Internal users can only access resources in their tenant
    if is_internal_role(user_role):
        # If user has no tenant_id, deny access (data integrity issue)
        if not user_tenant_id:
            return False

        # Check tenant match
        return user_tenant_id == resource_tenant_id

    # Unknown role, deny access
    return False
