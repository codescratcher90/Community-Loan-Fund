"""
Role-based Access Control
-------------------------
Resource + Operation model. Secure by default — no DB record = denied.

Runtime permission checks are stored in DynamoDB (via utils.app_settings).
This file defines the role hierarchy (for modification guards) and the
DEFAULT_RESOURCE_PERMISSIONS seed template.

To add a new endpoint:
  1. Add its resource + operation to DEFAULT_RESOURCE_PERMISSIONS below
     (or create a new resource key if it doesn't exist yet).
  2. Decorate the handler: @require_auth(resource='your_resource', operation='your_op')
  3. Call POST /settings/permissions/seed (master only) to push defaults to DynamoDB.
     Until seeded, the endpoint is master-only (secure by default).
"""


# ---------------------------------------------------------------------------
# Role Hierarchy
# Higher number = more privileges. Used for role-modification guards.
# ---------------------------------------------------------------------------
ROLE_HIERARCHY = {
    'master':      8,   # System operator — cross-tenant, god mode
    'owner':       7,   # Tenant owner — full control of their org
    'admin':       6,   # Tenant administrator
    'manager':     5,   # Tenant manager
    'supervisor':  4,   # Tenant supervisor
    'coordinator': 3,   # Tenant coordinator
    'staff':       2,   # Tenant staff member
    'customer':    1,   # External user — global, no tenant
}

VALID_ROLES    = list(ROLE_HIERARCHY.keys())
INTERNAL_ROLES = ['owner', 'admin', 'manager', 'supervisor', 'coordinator', 'staff']
EXTERNAL_ROLES = ['customer']
SYSTEM_ROLES   = ['master']


# ---------------------------------------------------------------------------
# Default Resource → Operation → Allowed Roles
#
# Written to DynamoDB once by POST /settings/permissions/seed.
# Runtime checks read from DynamoDB — NOT from this dict.
# Empty list [] = master only (master always bypasses the check).
#
# Add a new resource/operation here when you add a new endpoint group.
# ---------------------------------------------------------------------------
DEFAULT_RESOURCE_PERMISSIONS: dict[str, dict[str, list]] = {
    'users': {
        'list':        ['owner', 'admin', 'manager', 'supervisor'],
        'read':        ['owner', 'admin', 'manager', 'supervisor'],
        'create':      ['owner', 'admin'],
        'update_role': ['owner', 'admin'],
        'delete':      [],   # master only
    },
    'settings': {
        'read':   ['owner'],
        'update': [],        # master only
    },
    'permissions': {
        'read':   ['owner'],
        'update': [],        # master only
        # 'seed' and 'cache_clear' are intentionally absent → master only
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def has_permission(user_role: str, required_role: str) -> bool:
    """Hierarchy check — kept for can_modify_role and backward compat."""
    if required_role is None:
        return True
    user_level     = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


def can_modify_role(modifier_role: str, target_role: str, new_role: str) -> bool:
    """
    Can modifier change target's role to new_role?
    master can do anything; others cannot touch peers or superiors,
    and cannot promote anyone to their own level or above.
    """
    modifier_level = ROLE_HIERARCHY.get(modifier_role, 0)
    target_level   = ROLE_HIERARCHY.get(target_role, 0)
    new_level      = ROLE_HIERARCHY.get(new_role, 0)

    if modifier_role == 'master':
        return True
    if target_role == 'master' or new_role == 'master':
        return False
    if target_level >= modifier_level:
        return False
    if new_level >= modifier_level:
        return False
    return True


def check_tenant_access(
    user_role: str,
    user_tenant_id: str,
    resource_tenant_id: str,
    resource_owner_id: str = None,
    user_id: str = None,
) -> bool:
    """
    Tenant isolation check.
      master       → access everything
      internal role → only resources in their own tenant
      customer     → only their own resources (by owner id)
    """
    if user_role == 'master':
        return True

    if is_external_role(user_role):
        if resource_owner_id and user_id:
            return resource_owner_id == user_id
        return False

    if is_internal_role(user_role):
        if not user_tenant_id:
            return False
        return user_tenant_id == resource_tenant_id

    return False


# ---------------------------------------------------------------------------
# Role category helpers
# ---------------------------------------------------------------------------

def is_internal_role(role: str) -> bool:
    return role in INTERNAL_ROLES

def is_external_role(role: str) -> bool:
    return role in EXTERNAL_ROLES

def is_system_role(role: str) -> bool:
    return role in SYSTEM_ROLES

def requires_tenant(role: str) -> bool:
    return is_internal_role(role)
