# Architecture

## Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 on AWS Lambda |
| API | AWS API Gateway (REST) |
| Database | AWS DynamoDB (6 tables, PAY_PER_REQUEST) |
| Auth | JWT (PyJWT) + bcrypt |
| IaC | AWS SAM (`template.yaml`) |
| CI/CD | GitHub Actions |

---

## System Diagram

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  API Client │─────▶│ API Gateway  │─────▶│   Lambda    │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                                    ┌──────────────┼──────────────┐
                                    ▼              ▼              ▼
                               DynamoDB        DynamoDB        DynamoDB
                                Users          Tokens          Settings
```

## Request Flow

```
API Gateway
  └─ lambda_handler()
       ├─ OPTIONS → 200 CORS preflight (immediate)
       ├─ match_route(method, path) → find handler
       └─ middleware stack (outermost → innermost):
            rate_limit → require_auth → validate_request_body → handler
                                                                    └─ success_response / error_response
```

All responses share a standard envelope:
```json
{
  "success": true,
  "status_code": 200,
  "message": "...",
  "data": { "..." },
  "error": null,
  "meta": {}
}
```

---

## Project Structure

```
Basic-Auth/
├── lambda_function.py         # Entry point — routes requests to handlers
├── template.yaml              # SAM infrastructure (Lambda + API GW + DynamoDB)
├── requirements.txt           # boto3, PyJWT, bcrypt, python-dotenv
│
├── config/
│   ├── settings.py            # Config class — reads env vars
│   └── permissions.py        # Role hierarchy + action matrix + can_perform()
│
├── handlers/                  # One file per feature area
│   ├── register.py            # POST /auth/register, POST /auth/register-master
│   ├── login.py               # POST /auth/login
│   ├── logout.py              # POST /auth/logout
│   ├── refresh_token.py       # POST /auth/refresh
│   ├── verify.py              # POST /auth/verify
│   ├── profile.py             # GET/PUT /auth/me
│   ├── users.py               # GET/POST/PUT/DELETE /users and /users/{id}
│   └── settings.py            # GET/PUT /settings, GET/PUT /settings/permissions
│
├── middleware/
│   ├── auth.py                # @require_auth decorator (JWT validation + RBAC)
│   └── rate_limiting.py       # Per-IP and per-user rate limit decorators
│
├── utils/
│   ├── database.py            # DynamoDB wrappers: UserDB, RefreshTokenDB, etc.
│   ├── jwt_utils.py           # Token creation and validation
│   ├── password.py            # bcrypt hash/verify
│   ├── verification.py        # OTP generation + send (SES/SNS stubs)
│   ├── responses.py           # success_response / error_response helpers
│   ├── validators.py          # Email, phone, password, name validators
│   ├── schemas.py             # Request body schema definitions
│   ├── schema_validator.py    # SchemaField, Schema, @validate_request_body
│   └── app_settings.py        # Runtime settings + role permissions from DynamoDB
│
└── docs/                      # Project documentation
    ├── api-reference.md
    ├── architecture.md        # ← you are here
    ├── deployment.md
    ├── examples.md
    └── next-steps.md
```

---

## Role Hierarchy

The system has an **8-tier role hierarchy**. A higher number means more privileges.

| Role | Level | Category | Description |
|---|---|---|---|
| master | 8 | System | Cross-tenant god mode — the operator |
| owner | 7 | Internal | Tenant owner — full control of their org |
| admin | 6 | Internal | Tenant administrator |
| manager | 5 | Internal | Tenant manager |
| supervisor | 4 | Internal | Tenant supervisor |
| coordinator | 3 | Internal | Tenant coordinator |
| staff | 2 | Internal | Tenant staff member |
| customer | 1 | External | Global user — no tenant |

**Internal roles** (`owner` → `staff`) are scoped to a `tenant_id`.
**External roles** (`customer`) exist globally — no tenant, can interact with multiple orgs.
**System roles** (`master`) have no tenant, full cross-tenant access.

### Role Mapping Examples

Because the roles are generic, map them to whatever job titles fit your use case:

| Generic | Hotel | Restaurant | Gym | SaaS |
|---|---|---|---|---|
| owner | Hotel Owner | Chain Owner | Gym Owner | Company Admin |
| admin | General Manager | Regional Manager | Gym Manager | Team Lead |
| manager | Dept. Manager | Location Manager | Head Trainer | Project Manager |
| supervisor | Shift Supervisor | Shift Lead | Senior Trainer | Senior Dev |
| coordinator | Guest Relations | Event Coordinator | Class Coordinator | Coordinator |
| staff | Receptionist | Server / Chef | Trainer | Team Member |
| customer | Hotel Guest | Diner | Gym Member | End User |

---

## Permissions System

Permissions are stored in DynamoDB and checked at runtime via `can_perform(role, action)`.

### Named Actions

All capabilities are defined as constants in `config/permissions.py → Actions`:

```
register, register_master, verify, login, refresh_token   # public (no auth)
read_profile, update_profile, logout
list_users, read_user, create_user, update_user_role, delete_user
read_settings, update_settings
```

### Default Permission Matrix

| Action | owner | admin | manager | supervisor | coordinator | staff | customer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| logout | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| read_profile | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| update_profile | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| list_users | ✓ | ✓ | ✓ | ✓ | | | |
| read_user | ✓ | ✓ | ✓ | ✓ | | | |
| create_user | ✓ | ✓ | | | | | |
| update_user_role | ✓ | ✓ | | | | | |
| read_settings | ✓ | | | | | | |
| update_settings | — | — | — | — | — | — | — |

`master` implicitly has **all** actions and cannot be modified.

### Runtime Permission Changes

The master can change permissions for any role at runtime without redeploying code:

```bash
# Grant list_users to coordinator
curl -X PUT $API_URL/settings/permissions/coordinator \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"grant": ["list_users"]}'

# Revoke update_user_role from admin
curl -X PUT $API_URL/settings/permissions/admin \
  -d '{"revoke": ["update_user_role"]}'

# Full replace — set exact action set
curl -X PUT $API_URL/settings/permissions/staff \
  -d '{"actions": ["logout", "read_profile", "update_profile", "list_users"]}'

# View all current permissions
curl -X GET $API_URL/settings/permissions \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

Permissions are stored in the `app_settings` DynamoDB table under keys like `permissions:coordinator`.
On cold start, the Lambda seeds DynamoDB with code defaults if no entry exists yet.

### Adding a New Action (for developers)

1. Add a constant to `Actions` class in `config/permissions.py`
2. Add it to the roles that should have it in `ROLE_PERMISSIONS`
3. Use `@require_auth(action=Actions.YOUR_ACTION)` on the new handler

---

## Multi-Tenant Model

```
┌───────────────────────────────────────────┐
│  SYSTEM LEVEL                             │
│  master — full access to all tenants      │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│  TENANT LEVEL  (scoped to one org)        │
│  owner → admin → manager → supervisor    │
│       → coordinator → staff              │
│                                           │
│  Each user has tenant_id.                 │
│  Can only access resources in their org.  │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│  GLOBAL LEVEL  (no tenant)                │
│  customer — external user, no tenant_id   │
│  Can interact with multiple orgs.         │
│  Sees only their own resources.           │
└───────────────────────────────────────────┘
```

**Tenant isolation** is enforced by `check_tenant_access()` in `config/permissions.py`:
- `master` → any resource in any tenant
- Internal roles → only resources where `tenant_id` matches their own
- `customer` → only resources where they are the `resource_owner_id`

---

## DynamoDB Tables

All tables are named `{APP_NAME}-{ENVIRONMENT}-{table}` (e.g. `community-fund-prod-users`).

| Table | Primary Key | GSI | TTL |
|---|---|---|---|
| users | `user_id` (HASH) | `email-index` | No |
| refresh_tokens | `token` (HASH) | `user_id-index` | Yes (`expires_at`) |
| verification_codes | `user_id` (HASH) + `code_type` (RANGE) | — | No (bug — see next-steps §1.5) |
| login_attempts | `ip_address` (HASH) + `timestamp` (RANGE) | — | No (bug — see next-steps §1.6) |
| rate_limits | `limit_key` (HASH) | — | No |
| app_settings | `setting_key` (HASH) | — | No |

The `app_settings` table stores both general settings (e.g. `allow_public_signup`) and role
permissions (e.g. `permissions:coordinator → ["logout", "read_profile", ...]`).

---

## Environment Variables

Set automatically by SAM from `template.yaml`. For local dev create `.env`:

```env
APP_NAME=basic-auth
ENVIRONMENT=dev
JWT_SECRET=<openssl rand -base64 32>
REFRESH_TOKEN_SECRET=<openssl rand -base64 32>
MASTER_SECRET_KEY=<openssl rand -base64 32>
AWS_REGION=eu-north-1
```

Do **not** commit `.env` — it is in `.gitignore`.

---

## Security Notes

- **Secrets**: Use `openssl rand -base64 32` to generate JWT and master secrets
- **CORS**: `Access-Control-Allow-Origin: *` is fine for development; restrict to your frontend domain in production (see `next-steps.md §2.3`)
- **HTTPS**: API Gateway enforces HTTPS by default — no action needed
- **Bcrypt**: All passwords are hashed with bcrypt; cost factor is configurable
- **Rate limiting**: Per-IP and per-user limits are applied via middleware decorators
- **Account locking**: Configurable max failed login attempts and lockout duration via `/settings`
