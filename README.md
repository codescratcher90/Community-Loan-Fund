# Basic Auth API 🔐

A production-ready, serverless authentication API built with AWS Lambda, API Gateway, and DynamoDB. Features JWT-based authentication, role-based access control, rate limiting, and email/SMS verification.

## ✨ Features

- **JWT Authentication** - Secure token-based authentication with access and refresh tokens
- **User Management** - Complete CRUD operations for user accounts
- **Multi-Tenant Architecture** - Full tenant isolation for organizations with global customer support
- **Role-Based Access Control** - 8-tier role hierarchy (master, owner, admin, manager, supervisor, coordinator, staff, customer)
- **Email & SMS Verification** - Two-factor verification for new accounts
- **Rate Limiting** - Protection against brute force and abuse
- **Account Security** - Failed login tracking, account locking, and password hashing with bcrypt
- **Serverless Architecture** - Fully serverless using AWS Lambda and DynamoDB
- **Multi-Environment** - Support for dev, staging, and production environments

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│             │      │              │      │             │
│  API Client │─────▶│ API Gateway  │─────▶│   Lambda    │
│             │      │              │      │  Function   │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                                                   ▼
                                          ┌────────────────┐
                                          │   DynamoDB     │
                                          │   Tables:      │
                                          │   - Users      │
                                          │   - Tokens     │
                                          │   - Codes      │
                                          │   - Attempts   │
                                          │   - Limits     │
                                          └────────────────┘
```

## 🎭 Role Hierarchy & Multi-Tenant Architecture

### Role Structure

The system implements an 8-tier role hierarchy with multi-tenant support:

```
┌─────────────────────────────────────────────────────────┐
│  SYSTEM LEVEL                                           │
│  ┌────────┐                                             │
│  │ master │  System developer - Full access to all     │
│  └────────┘  tenants and users                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  TENANT LEVEL (Scoped to Organization)                  │
│  ┌───────┐                                              │
│  │ owner │  Organization owner                          │
│  └───┬───┘                                              │
│      │                                                   │
│  ┌───▼───┐                                              │
│  │ admin │  Organization administrator                  │
│  └───┬───┘                                              │
│      │                                                   │
│  ┌───▼────────┐                                         │
│  │  manager   │  Department/Team manager                │
│  └───┬────────┘                                         │
│      │                                                   │
│  ┌───▼──────────┐                                       │
│  │  supervisor  │  Team lead/Supervisor                 │
│  └───┬──────────┘                                       │
│      │                                                   │
│  ┌───▼────────────┐                                     │
│  │  coordinator   │  Project coordinator/Specialist     │
│  └───┬────────────┘                                     │
│      │                                                   │
│  ┌───▼─────┐                                            │
│  │  staff  │  Team member                               │
│  └─────────┘                                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  GLOBAL LEVEL (Not scoped to tenant)                    │
│  ┌──────────┐                                           │
│  │ customer │  External user - Can interact with        │
│  └──────────┘  multiple tenants                         │
└─────────────────────────────────────────────────────────┘
```

### Multi-Tenant Model

**Internal Users (Tenant-Scoped):**
- Roles: `owner`, `admin`, `manager`, `supervisor`, `coordinator`, `staff`
- Each user has a `tenant_id` linking them to their organization
- Can only access and manage resources within their tenant
- Example: Hotel A's staff can only see Hotel A's bookings

**External Users (Global):**
- Role: `customer`
- No `tenant_id` - exists globally across all tenants
- Can interact with multiple organizations
- Can view their own data across all tenants
- Example: A customer can book rooms at Hotel A, Hotel B, and Hotel C and see all bookings in one view

**System Users:**
- Role: `master`
- No `tenant_id` - full system access
- Can view and manage all tenants and users
- Can create new organizations (owners with new tenant_id)

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

1. **AWS CLI** (v2.x or higher)
   ```bash
   # Check version
   aws --version

   # Install: https://aws.amazon.com/cli/
   ```

2. **AWS SAM CLI** (v1.x or higher)
   ```bash
   # Check version
   sam --version

   # Install: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
   ```

3. **Docker** (for SAM build)
   ```bash
   # Check version
   docker --version

   # Install: https://docs.docker.com/get-docker/
   ```

4. **AWS Account** with appropriate permissions
   - IAM permissions to create Lambda functions, API Gateway, and DynamoDB tables
   - Configured AWS credentials

## 🚀 Deployment Options

Choose your deployment method:

### Option 1: GitHub Actions (Recommended - Zero Setup!) 🎯

**Automatic deployment with GitHub Actions - No local installation needed!**

This is the easiest way to deploy. Just configure secrets on GitHub and push your code!

👉 **[See GitHub Actions Setup Guide](GITHUB_ACTIONS_SETUP.md)** 👈

**Quick summary:**
1. Create IAM user in AWS
2. Add 6 secrets to GitHub repository settings
3. Push to `main` branch → Auto-deploys to dev!

[Full step-by-step guide →](GITHUB_ACTIONS_SETUP.md)

---

### Option 2: Manual Deployment (Local)

Deploy from your local machine using SAM CLI.

## 🚀 Quick Start (Manual Deployment)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Basic-Auth.git
cd Basic-Auth
```

### 2. Configure AWS Credentials

```bash
# Configure your AWS credentials
aws configure

# Verify your identity
aws sts get-caller-identity
```

### 3. Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and configure your secrets
nano .env  # or use your preferred editor
```

**Required configuration in `.env`:**

```bash
# Application Configuration
APP_NAME=basic-auth           # Your app name (customize for white-label deployments)
ENVIRONMENT=dev               # dev, staging, or prod

# Generate secure secrets using:
openssl rand -base64 32

# Update these values:
JWT_SECRET=<your-generated-secret>
REFRESH_TOKEN_SECRET=<your-generated-secret>
MASTER_SECRET_KEY=<your-generated-secret>

# Set your AWS region
AWS_REGION=eu-north-1  # or your preferred region
```

### 4. Customize Your Deployment (Optional but Recommended!)

**For White-Label / Multi-Tenant Deployments:**

You can customize the app name to deploy multiple instances or create white-label versions:

```bash
# Hotel Management System
export APP_NAME=hotel-manager
export ENVIRONMENT=prod
./deploy-sam.sh

# Restaurant POS System
export APP_NAME=restaurant-pos
export ENVIRONMENT=prod
./deploy-sam.sh

# Gym Management
export APP_NAME=gymflow
export ENVIRONMENT=dev
./deploy-sam.sh
```

**Benefits:**
- ✅ Multiple deployments in the same AWS account
- ✅ No resource name conflicts
- ✅ White-label your auth system for different clients
- ✅ Separate production, staging, and dev for each client

**Resource Naming:**
All resources will be named `{APP_NAME}-{ENVIRONMENT}-{resource}`:
- Tables: `hotel-manager-prod-users`, `hotel-manager-prod-tokens`
- Lambda: `hotel-manager-prod-api`
- API Gateway: `hotel-manager-prod-api`

### 5. Deploy to AWS

The deployment script will prompt for app name and environment if not set:

```bash
# Interactive deployment (prompts for app name and environment)
./deploy-sam.sh

# Or set via environment variables
APP_NAME=my-app ENVIRONMENT=dev ./deploy-sam.sh
```

**Example output:**
```
Enter application name (default: basic-auth): hotel-manager
Enter environment (dev/staging/prod) [default: dev]: prod

Deployment Configuration:
  App Name:    hotel-manager
  Environment: prod
  Stack Name:  hotel-manager-prod
```

The deployment script will:
- ✅ Validate prerequisites
- ✅ Build the Lambda package
- ✅ Create/update DynamoDB tables
- ✅ Deploy Lambda function
- ✅ Configure API Gateway
- ✅ Display your API endpoint URL

### 6. Test Your API

After deployment, you'll receive an API URL. Test it:

```bash
# Example API URL from deployment output
API_URL="https://xxxxxxxxxx.execute-api.eu-north-1.amazonaws.com/dev"

# Create a master user
curl -X POST $API_URL/auth/register-master \
  -H "Content-Type: application/json" \
  -d '{
    "secret_key": "your-master-secret-key",
    "email": "admin@example.com",
    "password": "SecurePass123",
    "first_name": "Admin",
    "last_name": "User"
  }'

# Login
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePass123"
  }'
```

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/register-master` | Create master user (requires secret) | No |
| POST | `/auth/verify` | Verify email/phone code | No |
| POST | `/auth/login` | Login user | No |
| POST | `/auth/refresh` | Refresh access token | No |
| POST | `/auth/logout` | Logout user | Yes |
| GET | `/auth/me` | Get current user profile | Yes |
| PUT | `/auth/me` | Update current user profile | Yes |

### User Management Endpoints

| Method | Endpoint | Description | Auth Required | Role Required | Tenant Isolation |
|--------|----------|-------------|---------------|---------------|------------------|
| GET | `/users` | List all users | Yes | Admin+ | Master: all users<br>Admin+: tenant users only |
| POST | `/users` | Create internal user | Yes | Admin+ | Master: any tenant<br>Admin+: own tenant only |
| GET | `/users/{id}` | Get user by ID | Yes | Admin+ | Master: any user<br>Admin+: tenant users only |
| PUT | `/users/{id}/role` | Update user role | Yes | Admin+ | Master: any user<br>Admin+: tenant users only |
| DELETE | `/users/{id}` | Delete user | Yes | Master | Master only - any user |

### Example Requests

#### Authentication Endpoints

<details>
<summary><b>1. Register New User - POST /auth/register</b></summary>

Register a new user account. Email and SMS verification codes will be sent.

**Request:**
```bash
curl -X POST https://your-api-url.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890"
  }'
```

**Response (201 Created):**
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
    "phone": "+1234567890",
    "role": "user",
    "is_verified": false,
    "created_at": "2025-12-26T10:30:00.000000"
  },
  "error": null,
  "meta": {}
}
```
</details>

<details>
<summary><b>2. Register Master User - POST /auth/register-master</b></summary>

Create a master user account. Requires the master secret key. Master users are automatically verified.

**Request:**
```bash
curl -X POST https://your-api-url.com/auth/register-master \
  -H "Content-Type: application/json" \
  -d '{
    "secret_key": "your-master-secret-key",
    "email": "admin@example.com",
    "password": "SecurePass123",
    "first_name": "Admin",
    "last_name": "User"
  }'
```

**Response (201 Created):**
```json
{
  "success": true,
  "status_code": 201,
  "message": "Master user created successfully",
  "data": {
    "user_id": "660f9511-f39c-52e5-b827-557766551111",
    "email": "admin@example.com",
    "first_name": "Admin",
    "last_name": "User",
    "phone": "",
    "role": "master",
    "is_verified": true,
    "created_at": "2025-12-26T10:35:00.000000"
  },
  "error": null,
  "meta": {}
}
```
</details>

<details>
<summary><b>3. Verify Email/SMS Code - POST /auth/verify</b></summary>

Verify the email or SMS verification code sent during registration.

**Request:**
```bash
curl -X POST https://your-api-url.com/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "code": "123456",
    "code_type": "email"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Email verified successfully",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "is_verified": true,
    "email_verified": true,
    "phone_verified": true
  },
  "error": null,
  "meta": {}
}
```

**Note:** For SMS verification, use `"code_type": "sms"`. The user is fully verified only when both email and phone (if provided) are verified.
</details>

<details>
<summary><b>4. Login - POST /auth/login</b></summary>

Authenticate a user and receive access and refresh tokens.

**Request:**
```bash
curl -X POST https://your-api-url.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Login successful",
  "data": {
    "user": {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+1234567890",
      "role": "user"
    },
    "tokens": {
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDAwIiwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIiwicm9sZSI6InVzZXIiLCJleHAiOjE3MDUzOTY4MDB9.example",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDAwIiwiZXhwIjoxNzA2MDAxNjAwfQ.example",
      "type": "Bearer",
      "expires_in": 1800
    }
  },
  "error": null,
  "meta": {}
}
```

**Note:** Access token expires in 30 minutes (1800 seconds), refresh token expires in 7 days.
</details>

<details>
<summary><b>5. Refresh Access Token - POST /auth/refresh</b></summary>

Get a new access token using a valid refresh token.

**Request:**
```bash
curl -X POST https://your-api-url.com/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.newtoken...",
    "token_type": "Bearer",
    "expires_in": 1800
  },
  "error": null,
  "meta": {}
}
```
</details>

<details>
<summary><b>6. Logout - POST /auth/logout</b></summary>

Logout user by revoking their refresh token. Requires authentication.

**Request:**
```bash
curl -X POST https://your-api-url.com/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Logged out successfully",
  "data": null,
  "error": null,
  "meta": {}
}
```
</details>

<details>
<summary><b>7. Get Current User Profile - GET /auth/me</b></summary>

Get the authenticated user's profile information.

**Request:**
```bash
curl -X GET https://your-api-url.com/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "role": "user",
    "is_verified": true,
    "is_locked": false,
    "created_at": "2025-12-26T10:30:00.000000",
    "updated_at": "2025-12-26T10:30:00.000000"
  },
  "error": null,
  "meta": {}
}
```
</details>

<details>
<summary><b>8. Update Current User Profile - PUT /auth/me</b></summary>

Update the authenticated user's profile. Can update name, phone, and password.

**Request:**
```bash
curl -X PUT https://your-api-url.com/auth/me \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "first_name": "Johnny",
    "last_name": "Doe",
    "phone": "+1987654321"
  }'
```

**Request (Change Password):**
```bash
curl -X PUT https://your-api-url.com/auth/me \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "current_password": "SecurePass123",
    "password": "NewSecurePass456"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Profile updated successfully",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "Johnny",
    "last_name": "Doe",
    "phone": "+1987654321",
    "role": "user",
    "updated_at": "2025-12-26T11:00:00.000000"
  },
  "error": null,
  "meta": {}
}
```

**Note:** To change password, you must provide `current_password` and the new `password`.
</details>

#### User Management Endpoints

<details>
<summary><b>9. List All Users - GET /users</b></summary>

Get a list of all users. Requires admin or master role.

**Request:**
```bash
curl -X GET "https://your-api-url.com/users?limit=100" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "users": [
      {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+1234567890",
        "role": "user",
        "is_verified": true,
        "is_locked": false,
        "created_at": "2025-12-26T10:30:00.000000"
      },
      {
        "user_id": "660f9511-f39c-52e5-b827-557766551111",
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "phone": "",
        "role": "master",
        "is_verified": true,
        "is_locked": false,
        "created_at": "2025-12-26T10:35:00.000000"
      }
    ],
    "count": 2
  },
  "error": null,
  "meta": {}
}
```

**Query Parameters:**
- `limit` (optional): Maximum number of users to return (default: 100)

**Note:**
- Master sees all users across all tenants
- Admin/Owner/etc. see only users in their tenant
</details>

<details>
<summary><b>10. Create Internal User - POST /users</b></summary>

Create a new internal user (owner, admin, staff, etc.). Requires admin or master role.

**Master Creating Owner (New Tenant):**
```bash
curl -X POST https://your-api-url.com/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "email": "hotel-owner@example.com",
    "password": "SecurePass123",
    "first_name": "Hotel",
    "last_name": "Owner",
    "phone": "+1234567890",
    "role": "owner",
    "tenant_id": "hotel-abc-123"
  }'
```

**Admin Creating Staff in Their Tenant:**
```bash
curl -X POST https://your-api-url.com/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "email": "staff@example.com",
    "password": "SecurePass123",
    "first_name": "Staff",
    "last_name": "Member",
    "phone": "+1987654321",
    "role": "staff"
  }'
```

**Response (201 Created):**
```json
{
  "success": true,
  "status_code": 201,
  "message": "Staff user created successfully",
  "data": {
    "user_id": "770f9522-g40d-63f6-c938-668877662222",
    "email": "staff@example.com",
    "first_name": "Staff",
    "last_name": "Member",
    "phone": "+1987654321",
    "role": "staff",
    "tenant_id": "hotel-abc-123",
    "is_verified": true,
    "created_at": "2025-12-26T12:00:00.000000"
  },
  "error": null,
  "meta": {}
}
```

**Valid Roles for Internal Users:**
- `owner` - Organization owner (master only)
- `admin` - Administrator
- `manager` - Manager
- `supervisor` - Supervisor
- `coordinator` - Coordinator
- `staff` - Staff member

**Notes:**
- Internal users are auto-verified (no email/SMS verification needed)
- Master can create owners with custom `tenant_id` or internal users for any tenant
- Admin+ can only create users within their own tenant
- Admin+ cannot create owners (master only)
- The new user inherits the creator's `tenant_id` (unless master specifies otherwise)
</details>

<details>
<summary><b>11. Get User by ID - GET /users/{id}</b></summary>

Get detailed information about a specific user. Requires admin or master role.

**Request:**
```bash
curl -X GET https://your-api-url.com/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "role": "user",
    "is_verified": true,
    "is_locked": false,
    "email_verified": true,
    "phone_verified": true,
    "failed_login_attempts": 0,
    "created_at": "2025-12-26T10:30:00.000000",
    "updated_at": "2025-12-26T10:30:00.000000"
  },
  "error": null,
  "meta": {}
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "status_code": 404,
  "message": "User not found",
  "data": null,
  "error": {
    "code": "NOT_FOUND"
  },
  "meta": {}
}
```
</details>

<details>
<summary><b>12. Update User Role - PUT /users/{id}/role</b></summary>

Update a user's role. Requires admin or master role.

**Request:**
```bash
curl -X PUT https://your-api-url.com/users/550e8400-e29b-41d4-a716-446655440000/role \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "role": "admin"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "User role updated to admin",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "role": "admin",
    "updated_at": "2025-12-26T11:15:00.000000"
  },
  "error": null,
  "meta": {}
}
```

**Valid Roles:**
- `user` - Regular user (default)
- `admin` - Administrator (can manage users, cannot create masters)
- `master` - Master administrator (full access)

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "status_code": 403,
  "message": "You don't have permission to change this user's role to the specified role",
  "data": null,
  "error": {
    "code": "FORBIDDEN"
  },
  "meta": {}
}
```
</details>

<details>
<summary><b>13. Delete User - DELETE /users/{id}</b></summary>

Delete a user account. Requires master role. Cannot delete your own account.

**Request:**
```bash
curl -X DELETE https://your-api-url.com/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "User deleted successfully",
  "data": null,
  "error": null,
  "meta": {}
}
```

**Error Response (400 Bad Request - Self Deletion):**
```json
{
  "success": false,
  "status_code": 400,
  "message": "Cannot delete your own account",
  "data": null,
  "error": null,
  "meta": {}
}
```

**Note:** This also deletes all associated refresh tokens for the user.
</details>

#### Error Response Examples

<details>
<summary><b>Validation Error (422)</b></summary>

```json
{
  "success": false,
  "status_code": 422,
  "message": "Validation failed",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "email": "Invalid email format",
      "password": "Password must be at least 8 characters"
    }
  },
  "meta": {}
}
```
</details>

<details>
<summary><b>Unauthorized (401)</b></summary>

```json
{
  "success": false,
  "status_code": 401,
  "message": "Invalid or expired token",
  "data": null,
  "error": {
    "code": "UNAUTHORIZED"
  },
  "meta": {}
}
```
</details>

<details>
<summary><b>Rate Limit Exceeded (429)</b></summary>

```json
{
  "success": false,
  "status_code": 429,
  "message": "Rate limit exceeded - Too many requests",
  "data": null,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED"
  },
  "meta": {}
}
```
</details>

## 🛠️ Development

### Using the Makefile

For convenience, use the included Makefile:

```bash
# Build the application
make build

# Deploy to dev
make deploy

# Deploy to specific environment
make deploy-staging
make deploy-prod

# Run tests
make test

# Clean build artifacts
make clean

# View logs
make logs

# Destroy stack (be careful!)
make destroy
```

### Local Development

```bash
# Install dependencies locally
pip install -r requirements.txt

# Run local API (requires Docker)
sam local start-api

# Test a single function locally
sam local invoke AuthFunction --event events/test-event.json
```

### Project Structure

```
Basic-Auth/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Configuration settings
│   └── permissions.py       # RBAC permissions
├── handlers/
│   ├── __init__.py
│   ├── register.py          # Registration handlers
│   ├── login.py             # Login handler
│   ├── logout.py            # Logout handler
│   ├── profile.py           # User profile handlers
│   ├── users.py             # User management handlers
│   ├── refresh_token.py     # Token refresh handler
│   └── verify.py            # Verification handler
├── middleware/
│   ├── __init__.py
│   ├── auth.py              # JWT authentication middleware
│   └── rate_limiting.py     # Rate limiting middleware
├── utils/
│   ├── __init__.py
│   ├── database.py          # DynamoDB utilities
│   ├── jwt_utils.py         # JWT token utilities
│   ├── password.py          # Password hashing
│   ├── responses.py         # Response helpers
│   ├── validators.py        # Input validation
│   └── verification.py      # Email/SMS verification
├── scripts/
│   ├── create_tables.py     # DynamoDB table creation
│   └── deploy.sh            # Legacy deployment script
├── lambda_function.py       # Main Lambda handler
├── template.yaml            # SAM/CloudFormation template
├── samconfig.toml           # SAM configuration
├── deploy-sam.sh            # SAM deployment script
├── Makefile                 # Convenience commands
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
└── README.md                # This file
```

## 🔒 Security Best Practices

1. **Strong Secrets**: Always use cryptographically secure random strings for JWT secrets
   ```bash
   openssl rand -base64 32
   ```

2. **Environment Variables**: Never commit `.env` file or expose secrets
   - Add `.env` to `.gitignore`
   - Use AWS Secrets Manager for production secrets

3. **CORS Configuration**: Update CORS settings in `template.yaml` for production
   ```yaml
   AllowOrigin: "'https://yourdomain.com'"  # Instead of '*'
   ```

4. **Password Policy**: Adjust minimum password length in `config/settings.py`
   ```python
   MIN_PASSWORD_LENGTH: int = 12  # Increase for production
   ```

5. **Rate Limiting**: Configure appropriate rate limits in `.env`

6. **HTTPS Only**: API Gateway enforces HTTPS by default

## 🌍 Multi-Environment Deployment

Deploy to different environments with separate resources:

```bash
# Development
./deploy-sam.sh dev
# Creates: basic-auth-dev stack

# Staging
./deploy-sam.sh staging
# Creates: basic-auth-staging stack

# Production
./deploy-sam.sh prod
# Creates: basic-auth-prod stack
```

Each environment has:
- Separate DynamoDB tables (`dev_users`, `staging_users`, `prod_users`)
- Separate Lambda functions
- Separate API Gateway endpoints
- Isolated configurations

## 📊 Monitoring and Logs

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/dev-basic-auth-api --follow

# View API Gateway logs (if enabled)
aws logs tail API-Gateway-Execution-Logs_<api-id>/dev --follow
```

### Metrics

Monitor these CloudWatch metrics:
- Lambda invocations, errors, duration
- API Gateway 4xx/5xx errors, latency
- DynamoDB read/write capacity, throttles

## 🗑️ Cleanup

To remove all resources and avoid AWS charges:

```bash
# Delete dev stack
aws cloudformation delete-stack --stack-name basic-auth-dev

# Delete staging stack
aws cloudformation delete-stack --stack-name basic-auth-staging

# Delete prod stack
aws cloudformation delete-stack --stack-name basic-auth-prod

# Or use SAM CLI
sam delete --stack-name basic-auth-dev
```

**Note**: This will delete all DynamoDB tables and data. Make sure to backup if needed!

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues

<details>
<summary><b>Error: AWS credentials not configured</b></summary>

```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=eu-north-1
```
</details>

<details>
<summary><b>Error: SAM CLI not found</b></summary>

Install AWS SAM CLI:
- **macOS**: `brew install aws-sam-cli`
- **Linux**: Follow [official guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **Windows**: Use MSI installer
</details>

<details>
<summary><b>Error: Docker not running</b></summary>

SAM requires Docker for building:
```bash
# Start Docker
# macOS/Windows: Start Docker Desktop
# Linux: sudo systemctl start docker
```
</details>

<details>
<summary><b>Deployment fails with permission errors</b></summary>

Ensure your IAM user/role has these permissions:
- `lambda:*`
- `apigateway:*`
- `dynamodb:*`
- `cloudformation:*`
- `iam:CreateRole`, `iam:AttachRolePolicy`
- `s3:*` (for SAM deployment artifacts)
</details>

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/Basic-Auth/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Basic-Auth/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/Basic-Auth/wiki)

## 🙏 Acknowledgments

Built with:
- [AWS Lambda](https://aws.amazon.com/lambda/)
- [AWS SAM](https://aws.amazon.com/serverless/sam/)
- [PyJWT](https://pyjwt.readthedocs.io/)
- [bcrypt](https://github.com/pyca/bcrypt/)
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

Made with ❤️ for the serverless community
