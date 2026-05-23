# Permissions Endpoints

The RBAC system maps `resource + operation` pairs to lists of allowed roles.
If no record exists in DynamoDB for a pair, access is **denied by default**
(fail-closed). Master always bypasses all permission checks.

---

## Contents

| # | Endpoint | Description |
|---|---|---|
| 1 | [GET /permissions](#get-permissions) | List configs for all resources |
| 2 | [GET /permissions/{resource}](#get-permissions-resource) | Get config for one resource |
| 3 | [PUT /permissions/{resource}](#put-permissions-resource) | Replace a resource's config |
| 4 | [POST /permissions/seed](#post-permissions-seed) | Write code defaults to DynamoDB |
| — | [Role Hierarchy](#role-hierarchy) | All roles and their privilege levels |

---

<a id="get-permissions"></a>

## 1. GET /permissions

```http
GET /permissions
```

List the stored permission config for every resource, plus the compile-time defaults.

**Auth:** Bearer token required. Role: master (or owner if seeded with read access)  
**Prerequisites:** A valid access token from `POST /auth/login`. Call endpoint 4 first if the system is freshly deployed.

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "resources": {
      "users": {
        "operations": {
          "list":        ["owner", "admin", "manager", "supervisor"],
          "read":        ["owner", "admin", "manager", "supervisor"],
          "create":      ["owner", "admin"],
          "update_role": ["owner", "admin"],
          "delete":      []
        },
        "created_at": "2025-05-23T10:00:00.000000",
        "updated_at": "2025-05-23T10:00:00.000000"
      }
    },
    "default_config": {
      "users": { "..." },
      "settings": { "..." },
      "permissions": { "..." }
    }
  }
}
```

`resources` is the live DynamoDB state. `default_config` is the compile-time
defaults (what endpoint 4 would write). If a key exists in `default_config`
but not in `resources`, that resource has not been seeded yet and is master-only.

An empty list (`[]`) for an operation means master-only access.

### Example

```bash
curl -X GET $API_URL/permissions \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

---

<a id="get-permissions-resource"></a>

## 2. GET /permissions/{resource}

```http
GET /permissions/{resource}
```

Get the stored permission config for a single resource.

**Auth:** Bearer token required. Role: master (or owner if seeded with read access)  
**Prerequisites:** A valid access token from `POST /auth/login`. The resource must have been seeded — if not, call endpoint 4 first.

### Path Parameters

| Parameter | Type | Notes |
|---|---|---|
| `resource` | string | Resource name, e.g. `users`, `settings`, `permissions` |

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "resource": "users",
    "operations": {
      "list":        ["owner", "admin", "manager", "supervisor"],
      "read":        ["owner", "admin", "manager", "supervisor"],
      "create":      ["owner", "admin"],
      "update_role": ["owner", "admin"],
      "delete":      []
    },
    "display_name": "Users",
    "description": "User management operations",
    "created_at": "2025-05-23T10:00:00.000000",
    "updated_at": "2025-05-23T10:00:00.000000"
  }
}
```

### Errors

| Status | When |
|---|---|
| `404` | No config found for this resource — call endpoint 4 first |

### Example

```bash
curl -X GET $API_URL/permissions/users \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

---

<a id="put-permissions-resource"></a>

## 3. PUT /permissions/{resource}

```http
PUT /permissions/{resource}
```

Replace the operations map for a resource. Any role not listed for an operation
is denied. `master` always has access regardless and cannot be added to the list.
Changes take effect immediately on the current Lambda container and within 60 s
on all others.

**Auth:** Bearer token required. Role: master only  
**Prerequisites:** A valid master access token from `POST /auth/login`

### Path Parameters

| Parameter | Type | Notes |
|---|---|---|
| `resource` | string | Resource name to update |

### Request Body

| Field | Type | Required | Notes |
|---|---|---|---|
| `operations` | object | yes | Map of `{operation: [roles]}` |
| `display_name` | string | no | Human-readable name — preserved if omitted |
| `description` | string | no | Description — preserved if omitted |

`operations` keys are arbitrary strings matching the `operation` parameter used
in `@require_auth(resource='...', operation='...')`. Values are arrays of role
names (all must be valid roles; `master` cannot be listed).

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Permissions updated for resource 'users'",
  "data": {
    "resource": "users",
    "operations": {
      "list":   ["owner", "admin"],
      "read":   ["owner", "admin"],
      "create": ["owner"],
      "delete": []
    },
    "created_at": "2025-05-23T10:00:00.000000",
    "updated_at": "2025-05-23T11:00:00.000000"
  }
}
```

### Errors

| Status | When |
|---|---|
| `400` | Missing or empty `operations` field |
| `422` | Unknown role name, or `master` listed as an allowed role |

### Example

```bash
# Restrict user creation to owner only
curl -X PUT $API_URL/permissions/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operations": {
      "list":        ["owner", "admin", "manager", "supervisor"],
      "read":        ["owner", "admin", "manager", "supervisor"],
      "create":      ["owner"],
      "update_role": ["owner", "admin"],
      "delete":      []
    }
  }'
```

---

<a id="post-permissions-seed"></a>

## 4. POST /permissions/seed

```http
POST /permissions/seed
```

Write the code-default permissions to DynamoDB. Safe to run multiple times
(idempotent — overwrites any existing config with the code defaults).

Run this after every deployment that adds a new endpoint. Until seeded, any
new endpoint is master-only.

**Auth:** Bearer token required. Role: master only  
**Prerequisites:** A valid master access token from `POST /auth/login`. Run once after first deployment, then again after each deployment that adds new endpoints.

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Seeded permissions for 3 resources",
  "data": {
    "seeded": ["users", "settings", "permissions"]
  }
}
```

### Example

```bash
curl -X POST $API_URL/permissions/seed \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

---

<a id="role-hierarchy"></a>

## Role Hierarchy

Roles ordered from highest to lowest privilege:

| Role | Level | Type | Description |
|---|---|---|---|
| `master` | 8 | System | Full system access, cross-tenant. Bypasses all permission checks. |
| `owner` | 7 | Internal | Full control within their tenant |
| `admin` | 6 | Internal | Tenant administrator |
| `manager` | 5 | Internal | Tenant manager |
| `supervisor` | 4 | Internal | Tenant supervisor |
| `coordinator` | 3 | Internal | Tenant coordinator |
| `staff` | 2 | Internal | Tenant staff member |
| `customer` | 1 | External | Public user, no tenant |

Internal roles (`owner` → `staff`) belong to a tenant and are scoped to it.
`customer` is global (no tenant). `master` is cross-tenant and bypasses all
permission checks.

---

## Related

- [Users](users.md) — role hierarchy applied to all user operations
- [Settings](settings.md) — configure alongside permissions after each deployment
