# Permissions Endpoints

The RBAC system controls which roles can call which operations. Every endpoint is
protected by a `resource + operation` pair. If no record exists in DynamoDB for
that pair, access is **denied by default** (fail-closed). Master always bypasses
all permission checks.

---

## GET /permissions

List the stored permission config for every resource.

**Auth:** Bearer token required. Role: **master only** (default; owner can read if seeded that way).

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
      },
      "settings": {
        "operations": {
          "read":   ["owner"],
          "update": []
        },
        ...
      }
    },
    "default_config": {
      "users": { ... },
      "settings": { ... },
      "permissions": { ... }
    }
  }
}
```

`default_config` is the compile-time defaults from code (what `POST /permissions/seed`
would write). `resources` is the live DynamoDB state. If a key exists in `default_config`
but not in `resources`, that resource has not been seeded yet and is master-only.

### Example

```bash
curl -X GET $API_URL/permissions \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

---

## GET /permissions/{resource}

Get the stored permission config for a single resource.

**Auth:** Bearer token required. Role: master (or owner if seeded with read access).

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

An empty list (`[]`) for an operation means master-only access.

### Errors

| Status | When |
|---|---|
| 404 | No config found — call `POST /permissions/seed` first |

### Example

```bash
curl -X GET $API_URL/permissions/users \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

---

## PUT /permissions/{resource}

Replace the operations map for a resource. Any roles not listed for an operation
will be denied. `master` always has access regardless of what is listed (and cannot
be added to the list).

**Auth:** Bearer token required. Role: **master only**.

### Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `operations` | object | yes | Map of `{operation: [roles]}` |
| `display_name` | string | no | Human-readable name — preserved if omitted |
| `description` | string | no | Description — preserved if omitted |

`operations` keys are arbitrary strings matching the `operation` parameter in
`@require_auth(resource='...', operation='...')`. Values are arrays of role names
(all must be valid roles excluding `master`).

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
| 400 | Missing or empty `operations` field |
| 422 | Unknown role name, or `master` listed as an allowed role |

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

## POST /permissions/seed

Write the code-default permissions to DynamoDB. Safe to run multiple times
(idempotent — overwrites any existing config with the code defaults).

Run this after every deployment that adds a new endpoint, to initialise that
endpoint's default access rules.

**Auth:** Bearer token required. Role: **master only**.

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

## Role Hierarchy

Roles in order from highest to lowest privilege:

| Role | Level | Type | Description |
|---|---|---|---|
| `master` | 8 | System | Full system access, cross-tenant |
| `owner` | 7 | Internal | Full control within their tenant |
| `admin` | 6 | Internal | Tenant administrator |
| `manager` | 5 | Internal | Tenant manager |
| `supervisor` | 4 | Internal | Tenant supervisor |
| `coordinator` | 3 | Internal | Tenant coordinator |
| `staff` | 2 | Internal | Tenant staff member |
| `customer` | 1 | External | Public user, no tenant |

Internal roles (`owner` → `staff`) belong to a tenant. `customer` is global (no tenant).
`master` is cross-tenant and bypasses all permission checks.
