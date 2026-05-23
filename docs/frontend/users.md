# User Management Endpoints

Create, read, update, and delete users. Internal users (staff, admin, owner) are
created here and bypass OTP verification — they can log in immediately. Public
users register via `POST /auth/register`.

---

## Contents

| Endpoint | Description |
|---|---|
| [`GET /users`](#get-users) | List users (tenant-scoped) |
| [`POST /users`](#post-users) | Create an internal user |
| [`GET /users/{id}`](#get-users-id) | Get a single user by ID |
| [`PUT /users/{id}/role`](#put-users-id-role) | Change a user's role |
| [`DELETE /users/{id}`](#delete-users-id) | Permanently delete a user |

---

<a id="get-users"></a>

## `GET /users`

```http
GET /users
```

List users. Master sees all users across all tenants; internal roles (owner,
admin, manager, supervisor) see only users within their own tenant.

**Auth:** Bearer token required. Role: owner or above  
**Prerequisites:** A valid access token from `POST /auth/login` with sufficient role

### Query Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `limit` | integer | `100` | Max users to return |

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "users": [
      {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "john@example.com",
        "phone": "+12025550100",
        "first_name": "John",
        "last_name": "Doe",
        "role": "staff",
        "tenant_id": "tenant-abc-001",
        "email_verified": true,
        "phone_verified": false,
        "is_locked": false,
        "created_at": "2025-05-23T10:30:00.000000"
      }
    ],
    "count": 1
  }
}
```

### Errors

| Status | When |
|---|---|
| `401` | Missing or invalid token |
| `403` | Role not permitted |

### Examples

```bash
curl -X GET $API_URL/users \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# With limit
curl -X GET "$API_URL/users?limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

<a id="post-users"></a>

## `POST /users`

```http
POST /users
```

Create an internal user (pre-verified, with a role and tenant). Internal users
bypass the OTP verification flow — they are ready to log in immediately.

**Auth:** Bearer token required. Role: admin or above  
**Prerequisites:** A valid access token from `POST /auth/login` with admin or higher role. The `allow_adding_new_users` setting must be `true` (default). Cannot create `customer` role users via this endpoint — use `POST /auth/register` instead.

### Request Body

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | yes | |
| `password` | string | yes | Must meet `min_password_length` |
| `first_name` | string | yes | |
| `last_name` | string | yes | |
| `role` | string | no | Default: `staff`. Must be below caller's own role |
| `phone` | string | no | |
| `tenant_id` | string | conditional | Required for master when creating non-owner internal users |

### Role Creation Rules

| Caller role | Can create |
|---|---|
| `master` | Any role. For `owner`, a new `tenant_id` is auto-generated if not supplied |
| `owner` / `admin` | Any internal role below their own, within their tenant only |
| Any | Cannot create `customer` via this endpoint |

### Response `201`

```json
{
  "success": true,
  "status_code": 201,
  "message": "Staff user created successfully",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "employee@example.com",
    "phone": null,
    "first_name": "Jane",
    "last_name": "Smith",
    "role": "staff",
    "tenant_id": "tenant-abc-001",
    "email_verified": true,
    "phone_verified": false,
    "created_at": "2025-05-23T10:30:00.000000"
  }
}
```

### Errors

| Status | When |
|---|---|
| `403` | `allow_adding_new_users` is false |
| `403` | Trying to create an `owner` as non-master |
| `403` | Trying to create a `customer` via this endpoint |
| `403` | Target role is at or above caller's own level |
| `409` | Email already registered |
| `422` | Validation failed |

### Examples

```bash
# Create a staff member (as owner/admin)
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "employee@example.com",
    "password": "TempPass123",
    "first_name": "Jane",
    "last_name": "Smith",
    "role": "staff"
  }'

# Create an owner with a new tenant (master only)
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@newcompany.com",
    "password": "TempPass123",
    "first_name": "New",
    "last_name": "Owner",
    "role": "owner",
    "tenant_id": "company-new-001"
  }'
```

---

<a id="get-users-id"></a>

## `GET /users/{id}`

```http
GET /users/{id}
```

Get a single user by ID. Master can view any user; internal roles can only view
users within their own tenant.

**Auth:** Bearer token required. Role: owner or above  
**Prerequisites:** A valid access token from `POST /auth/login` with sufficient role. Non-master callers can only access users in their own tenant.

### Path Parameters

| Parameter | Type | Notes |
|---|---|---|
| `id` | string (UUID) | The `user_id` of the target user |

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "phone": null,
    "first_name": "John",
    "last_name": "Doe",
    "role": "staff",
    "tenant_id": "tenant-abc-001",
    "email_verified": true,
    "phone_verified": false,
    "is_locked": false,
    "failed_login_attempts": 0,
    "created_at": "2025-05-23T10:30:00.000000",
    "updated_at": "2025-05-23T11:00:00.000000"
  }
}
```

### Errors

| Status | When |
|---|---|
| `403` | Target user is in a different tenant (non-master caller) |
| `404` | User not found |

### Example

```bash
curl -X GET $API_URL/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

<a id="put-users-id-role"></a>

## `PUT /users/{id}/role`

```http
PUT /users/{id}/role
```

Change a user's role. Also manages tenant assignment: promoting to an internal
role assigns the target to the caller's tenant; demoting to `customer` clears
`tenant_id`.

**Auth:** Bearer token required. Role: admin or above  
**Prerequisites:** A valid access token from `POST /auth/login`. Caller's role must be strictly above both the target user's current role and the new role. Non-master callers can only modify users in their own tenant.

### Path Parameters

| Parameter | Type | Notes |
|---|---|---|
| `id` | string (UUID) | The `user_id` of the target user |

### Request Body

| Field | Type | Required | Notes |
|---|---|---|---|
| `role` | string | yes | Target role |
| `tenant_id` | string | no | Master only — override the tenant assigned on promotion |

### Role Change Rules

- You cannot change the role of a user at or above your own level.
- You cannot promote a user to your own level or above.
- Only master can touch other master accounts.

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "User role updated to admin",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "role": "admin",
    "tenant_id": "tenant-abc-001",
    "updated_at": "2025-05-23T11:00:00.000000"
  }
}
```

### Errors

| Status | When |
|---|---|
| `403` | Target user is at or above caller's role level |
| `403` | New role is at or above caller's role level |
| `403` | Target user is in a different tenant (non-master) |
| `404` | User not found |
| `422` | Invalid role value |

### Example

```bash
curl -X PUT $API_URL/users/550e8400-e29b-41d4-a716-446655440000/role \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

---

<a id="delete-users-id"></a>

## `DELETE /users/{id}`

```http
DELETE /users/{id}
```

Permanently delete a user and revoke all their refresh tokens.

**Auth:** Bearer token required. Role: **master only**  
**Prerequisites:** A valid master access token. Cannot delete your own account.

### Path Parameters

| Parameter | Type | Notes |
|---|---|---|
| `id` | string (UUID) | The `user_id` of the target user |

### Response `200`

```json
{
  "success": true,
  "status_code": 200,
  "message": "User deleted successfully",
  "data": null
}
```

### Errors

| Status | When |
|---|---|
| `400` | Attempting to delete your own account |
| `404` | User not found |

### Example

```bash
curl -X DELETE $API_URL/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

---

> ← Previous: [Profile](profile.md) &nbsp;|&nbsp; Next → [Settings](settings.md)
