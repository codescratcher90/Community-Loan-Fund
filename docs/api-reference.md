# API Reference

The full API reference is split by endpoint group. Start with the overview for
the response envelope format, authentication, OTP types, and status codes.

---

## Frontend Documentation

| Document | Covers |
|---|---|
| [Overview](frontend/overview.md) | Base URL, response envelope, all endpoints table, OTP types, status codes, error codes, flows |
| [Authentication](frontend/auth.md) | `/auth/register`, `/auth/verify`, `/auth/resend-otp`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/register-master` |
| [Profile](frontend/profile.md) | `GET /auth/me`, `PUT /auth/me` |
| [Users](frontend/users.md) | `GET /users`, `POST /users`, `GET /users/{id}`, `PUT /users/{id}/role`, `DELETE /users/{id}` |
| [Settings](frontend/settings.md) | `GET /settings`, `PUT /settings` |
| [Permissions](frontend/permissions.md) | `GET /permissions`, `GET /permissions/{resource}`, `PUT /permissions/{resource}`, `POST /permissions/seed` |

---

## Quick Reference

### All Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | None | Register with email, phone, or both |
| POST | `/auth/register-master` | Secret key in body | Bootstrap first master user |
| POST | `/auth/verify` | None | Submit OTP code |
| POST | `/auth/resend-otp` | None | Resend a pending OTP |
| POST | `/auth/login` | None | Login — returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh token in body | Get new access token |
| POST | `/auth/logout` | Bearer token | Revoke refresh token |
| GET | `/auth/me` | Bearer token | Get own profile |
| PUT | `/auth/me` | Bearer token | Update profile |
| GET | `/users` | Bearer (owner+) | List users |
| POST | `/users` | Bearer (admin+) | Create internal user |
| GET | `/users/{id}` | Bearer (owner+) | Get user by ID |
| PUT | `/users/{id}/role` | Bearer (admin+) | Change user role |
| DELETE | `/users/{id}` | Bearer (master) | Delete user |
| GET | `/settings` | Bearer (owner+) | Get app settings |
| PUT | `/settings` | Bearer (master) | Update app settings |
| GET | `/permissions` | Bearer (master) | List all RBAC configs |
| GET | `/permissions/{resource}` | Bearer (master) | Get one resource's config |
| PUT | `/permissions/{resource}` | Bearer (master) | Replace a resource's config |
| POST | `/permissions/seed` | Bearer (master) | Write code defaults to DB |

### Response Envelope

Every response uses the same shape:

```json
{
  "success": true,
  "status_code": 200,
  "message": "Human-readable summary",
  "data": {},
  "error": null,
  "meta": {}
}
```

On error, `success` is `false`, `data` is `null`, and `error` is populated:

```json
{
  "success": false,
  "status_code": 422,
  "message": "Validation failed",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "email": "Invalid email format"
    }
  },
  "meta": {}
}
```
