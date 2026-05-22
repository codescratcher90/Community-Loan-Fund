"""
Role-based Access Control
-------------------------
Two-layer system:
  1. Role hierarchy  — numeric levels for "can user A modify user B?"
  2. Action matrix   — explicit named actions for "can role X do Y?"

To add a new role:
  1. Add it to ROLE_HIERARCHY with an appropriate level
  2. Add it to INTERNAL_ROLES, EXTERNAL_ROLES, or SYSTEM_ROLES
  3. Add its allowed actions to ROLE_PERMISSIONS

To add a new action:
  1. Add a constant to the Actions class
  2. Add it to the roles that should have it in ROLE_PERMISSIONS
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

VALID_ROLES      = list(ROLE_HIERARCHY.keys())
INTERNAL_ROLES   = ['owner', 'admin', 'manager', 'supervisor', 'coordinator', 'staff']
EXTERNAL_ROLES   = ['customer']
SYSTEM_ROLES     = ['master']


# ---------------------------------------------------------------------------
# Named Actions
# Add a constant here when you introduce a new capability.
# ---------------------------------------------------------------------------
class Actions:
    # Public (no auth needed)
    REGISTER        = 'register'
    REGISTER_MASTER = 'register_master'
    VERIFY          = 'verify'
    LOGIN           = 'login'
    REFRESH_TOKEN   = 'refresh_token'

    # Own profile
    READ_PROFILE    = 'read_profile'
    UPDATE_PROFILE  = 'update_profile'
    LOGOUT          = 'logout'

    # User management
    LIST_USERS      = 'list_users'
    READ_USER       = 'read_user'
    CREATE_USER     = 'create_user'
    UPDATE_USER_ROLE = 'update_user_role'
    DELETE_USER     = 'delete_user'

    # Settings
    READ_SETTINGS   = 'read_settings'
    UPDATE_SETTINGS = 'update_settings'


# Actions that require no authentication at all
PUBLIC_ACTIONS = {
    Actions.REGISTER,
    Actions.REGISTER_MASTER,
    Actions.VERIFY,
    Actions.LOGIN,
    Actions.REFRESH_TOKEN,
}


# ---------------------------------------------------------------------------
# Role → Action Matrix
# master implicitly has ALL actions.
# To expand a role's access, add actions to its set here.
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS: dict[str, set[str]] = {
    'owner': {
        Actions.LOGOUT,
        Actions.READ_PROFILE,
        Actions.UPDATE_PROFILE,
        Actions.LIST_USERS,
        Actions.READ_USER,
        Actions.CREATE_USER,
        Actions.UPDATE_USER_ROLE,
        Actions.READ_SETTINGS,
    },
    'admin': {
        Actions.LOGOUT,
        Actions.READ_PROFILE,
        Actions.UPDATE_PROFILE,
        Actions.LIST_USERS,
        Actions.READ_USER,
        Actions.CREATE_USER,
        Actions.UPDATE_USER_ROLE,
    },
    'manager': {
        Actions.LOGOUT,
        Actions.READ_PROFILE,
        Actions.UPDATE_PROFILE,
        Actions.LIST_USERS,
        Actions.READ_USER,
    },
    'supervisor': {
        Actions.LOGOUT,
        Actions.READ_PROFILE,
        Actions.UPDATE_PROFILE,
        Actions.LIST_USERS,
        Actions.READ_USER,
    },
    'coordinator': {
        Actions.LOGOUT,
        Actions.READ_PROFILE,
        Actions.UPDATE_PROFILE,
    },
    'staff': {
        Actions.LOGOUT,
        Actions.READ_PROFILE,
        Actions.UPDATE_PROFILE,
    },
    'customer': {
        Actions.LOGOUT,
        Actions.READ_PROFILE,
        Actions.UPDATE_PROFILE,
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def can_perform(role: str, action: str) -> bool:
    """
    Check whether a role is allowed to perform a named action.
    master can do everything. Public actions need no role at all.
    """
    if action in PUBLIC_ACTIONS:
        return True
    if role == 'master':
        return True
    return action in ROLE_PERMISSIONS.get(role, set())


def has_permission(user_role: str, required_role: str) -> bool:
    """
    Hierarchy check: is user_role at least as privileged as required_role?
    Kept for backward compatibility with existing @require_auth(required_role=...) calls.
    """
    if required_role is None:
        return True
    user_level    = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


def can_modify_role(modifier_role: str, target_role: str, new_role: str) -> bool:
    """
    Can modifier change target's role to new_role?
    Rules: master can do anything; others cannot touch peers or superiors,
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
