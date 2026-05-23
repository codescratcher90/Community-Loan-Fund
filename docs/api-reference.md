# API Reference

All responses share this envelope:

```json
{
  "success": true,
  "status_code": 200,
  "message": "...",
  "data": {},
  "error": null,
  "meta": {}
}
```

---

## Endpoints

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Public user registration |
| POST | `/auth/register-master` | Secret key in body | Create master user |
| POST | `/auth/verify` | None | Submit email/SMS OTP code |
| POST | `/auth/login` | None | Login — returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh token in body | Get new access token |
| POST | `/auth/logout` | Bearer token | Revoke refresh token |
| GET | `/auth/me` | Bearer token | Get own profile |
| PUT | `/auth/me` | Bearer token | Update own profile |

### User Management

| Method | Path | Min Role | Tenant Scope |
|---|---|---|---|
| GET | `/users` | manager | master: all users · internal: own tenant |
| POST | `/users` | admin | master: any tenant · internal: own tenant |
| GET | `/users/{id}` | manager | master: any · internal: own tenant |
| PUT | `/users/{id}/role` | admin | master: any · internal: own tenant |
| DELETE | `/users/{id}` | master | master only |

### Settings (master only)

| Method | Path | Description |
|---|---|---|
| GET | `/settings` | Get all app settings |
| PUT | `/settings` | Update app settings |
| GET | `/settings/permissions` | Get all role permission sets + available actions |
| PUT | `/settings/permissions/{role}` | Replace / grant / revoke actions for a role |

---

## Request & Response Examples

<details>
<summary><b>POST /auth/register</b></summary>

```bash
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890"
  }'
```

```json
{
  "success": true,
  "status_code": 201,
  "message": "Registration successful. Please verify your email and phone.",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer",
    "is_verified": false,
    "created_at": "2025-12-26T10:30:00.000000"
  }
}
```
</details>

<details>
<summary><b>POST /auth/register-master</b></summary>

```bash
curl -X POST $API_URL/auth/register-master \
  -H "Content-Type: application/json" \
  -d '{
    "secret_key": "YOUR_MASTER_SECRET_KEY",
    "email": "admin@example.com",
    "password": "SecurePass123",
    "first_name": "Admin",
    "last_name": "User"
  }'
```

```json
{
  "success": true,
  "status_code": 201,
  "message": "Master user created successfully",
  "data": {
    "user_id": "660f9511-...",
    "email": "admin@example.com",
    "role": "master",
    "is_verified": true
  }
}
```
</details>

<details>
<summary><b>POST /auth/verify</b></summary>

```bash
curl -X POST $API_URL/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-...",
    "code": "123456",
    "code_type": "email"
  }'
```

`code_type` is `"email"` or `"sms"`. The user is fully verified when both email and phone (if provided) are verified.

```json
{
  "success": true,
  "status_code": 200,
  "message": "Email verified successfully",
  "data": {
    "user_id": "550e8400-...",
    "is_verified": true,
    "email_verified": true,
    "phone_verified": true
  }
}
```
</details>

<details>
<summary><b>POST /auth/login</b></summary>

```bash
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123"}'
```

```json
{
  "success": true,
  "status_code": 200,
  "message": "Login successful",
  "data": {
    "user": {
      "user_id": "550e8400-...",
      "email": "user@example.com",
      "first_name": "John",
      "role": "customer"
    },
    "tokens": {
      "access": "eyJhbGci...",
      "refresh": "eyJhbGci...",
      "type": "Bearer",
      "expires_in": 1800
    }
  }
}
```

Access token expires in 30 min (1800 s). Refresh token expires in 30 days.
</details>

<details>
<summary><b>POST /auth/refresh</b></summary>

```bash
curl -X POST $API_URL/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGci..."}'
```

```json
{
  "success": true,
  "status_code": 200,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJhbGci...",
    "token_type": "Bearer",
    "expires_in": 1800
  }
}
```
</details>

<details>
<summary><b>POST /auth/logout</b></summary>

```bash
curl -X POST $API_URL/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGci..."}'
```

```json
{"success": true, "status_code": 200, "message": "Logged out successfully", "data": null}
```
</details>

<details>
<summary><b>GET /auth/me</b></summary>

```bash
curl -X GET $API_URL/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "user_id": "550e8400-...",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "role": "customer",
    "is_verified": true,
    "is_locked": false,
    "created_at": "2025-12-26T10:30:00.000000",
    "updated_at": "2025-12-26T10:30:00.000000"
  }
}
```
</details>

<details>
<summary><b>PUT /auth/me — update profile</b></summary>

```bash
# Update name / phone
curl -X PUT $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Johnny", "phone": "+1987654321"}'

# Change password
curl -X PUT $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password": "SecurePass123", "password": "NewSecurePass456"}'
```

Changing password requires `current_password`.
</details>

<details>
<summary><b>GET /users — list users</b></summary>

```bash
curl -X GET "$API_URL/users?limit=100" -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "users": [
      {
        "user_id": "550e8400-...",
        "email": "staff@hotel.com",
        "role": "staff",
        "tenant_id": "hotel-abc-123",
        "is_verified": true,
        "is_locked": false,
        "created_at": "2025-12-26T11:00:00.000000"
      }
    ],
    "count": 1
  }
}
```

Master sees all users. Internal roles see only their tenant's users.
</details>

<details>
<summary><b>POST /users — create internal user</b></summary>

```bash
# Master creates an owner for a new tenant
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@hotel.com",
    "password": "SecurePass123",
    "first_name": "Hotel",
    "last_name": "Owner",
    "role": "owner",
    "tenant_id": "hotel-abc-123"
  }'

# Admin creates staff in their own tenant (no tenant_id needed)
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "staff@hotel.com",
    "password": "Staff123",
    "first_name": "Alice",
    "last_name": "Smith",
    "role": "staff"
  }'
```

Internal users are auto-verified (no OTP needed). Admin+ cannot create owners.
</details>

<details>
<summary><b>PUT /users/{id}/role</b></summary>

```bash
curl -X PUT $API_URL/users/550e8400-.../role \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

Rules:
- Cannot promote to your own level or above
- Cannot change the role of a peer or superior
- Cannot assign or remove the `master` role (master only modifies others, not itself)
</details>

<details>
<summary><b>DELETE /users/{id}</b></summary>

```bash
curl -X DELETE $API_URL/users/550e8400-... -H "Authorization: Bearer $MASTER_TOKEN"
```

Master only. Cannot delete your own account. Also deletes all refresh tokens for the user.
</details>

<details>
<summary><b>GET /settings</b></summary>

```bash
curl -X GET $API_URL/settings -H "Authorization: Bearer $MASTER_TOKEN"
```

```json
{
  "data": {
    "allow_public_signup": true,
    "allow_adding_new_users": true,
    "require_otp_on_registration": true,
    "email_verification_required": true,
    "default_public_role": "customer",
    "min_password_length": 4,
    "max_failed_login_attempts": 5,
    "account_lockout_duration_minutes": 30
  }
}
```
</details>

<details>
<summary><b>PUT /settings</b></summary>

```bash
curl -X PUT $API_URL/settings \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "min_password_length": 12,
    "max_failed_login_attempts": 3,
    "account_lockout_duration_minutes": 60
  }'
```

Partial updates only — omit fields you don't want to change.
</details>

<details>
<summary><b>GET /settings/permissions</b></summary>

```bash
curl -X GET $API_URL/settings/permissions -H "Authorization: Bearer $MASTER_TOKEN"
```

```json
{
  "data": {
    "permissions": {
      "owner": {"actions": ["create_user", "list_users", "logout", "..."], "source": "database"},
      "staff": {"actions": ["logout", "read_profile", "update_profile"], "source": "default"}
    },
    "all_actions": ["create_user", "delete_user", "list_users", "login", "logout", "..."]
  }
}
```

`source` is `"database"` if the permission set has been customised via the API, or `"default"` if still using code defaults.
</details>

<details>
<summary><b>PUT /settings/permissions/{role}</b></summary>

Three modes — pick one per request:

```bash
# Full replace — set an exact action set
curl -X PUT $API_URL/settings/permissions/coordinator \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"actions": ["logout", "read_profile", "update_profile", "list_users"]}'

# Grant — add actions to the current set
curl -X PUT $API_URL/settings/permissions/coordinator \
  -d '{"grant": ["list_users", "read_user"]}'

# Revoke — remove actions from the current set
curl -X PUT $API_URL/settings/permissions/admin \
  -d '{"revoke": ["update_user_role"]}'

# Grant and revoke in one call
curl -X PUT $API_URL/settings/permissions/manager \
  -d '{"grant": ["create_user"], "revoke": ["update_user_role"]}'
```

Cannot modify `master` permissions. Returns the updated action list.
</details>

---

## Error Responses

### 401 Unauthorized
```json
{
  "success": false,
  "status_code": 401,
  "message": "Invalid or expired token",
  "error": {"code": "UNAUTHORIZED"}
}
```

### 403 Forbidden
```json
{
  "success": false,
  "status_code": 403,
  "message": "You do not have permission to perform this action",
  "error": {"code": "FORBIDDEN"}
}
```

### 422 Validation Error
```json
{
  "success": false,
  "status_code": 422,
  "message": "Validation failed",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "email": "Invalid email format",
      "password": "Password must be at least 8 characters"
    }
  }
}
```

### 429 Rate Limit
```json
{
  "success": false,
  "status_code": 429,
  "message": "Rate limit exceeded - Too many requests",
  "error": {"code": "RATE_LIMIT_EXCEEDED"}
}
```
