# Real-World Deployment Examples

Complete end-to-end examples of deploying Basic-Auth for different use cases.
See [architecture.md](architecture.md) for the role hierarchy and [deployment.md](deployment.md) for setup instructions.

---

## Table of Contents

1. [Hotel Management System](#1-hotel-management-system)
2. [Restaurant POS System](#2-restaurant-pos-system)
3. [Gym / Fitness Platform](#3-gym--fitness-platform)
4. [SaaS Multi-Tenant Platform](#4-saas-multi-tenant-platform)
5. [E-Learning Platform](#5-e-learning-platform)
6. [Healthcare Clinic System](#6-healthcare-clinic-system)
7. [Common Workflows](#common-workflows)
8. [Testing Tenant Isolation](#testing-tenant-isolation)
9. [Deployment Checklist](#deployment-checklist)

---

## 1. Hotel Management System

### Scenario

Multi-hotel chain where each hotel manages its own staff (receptionists, managers) while
guests (customers) can book across hotels.

### Structure

```
System Master (You)
└─ Creates owners for each hotel

Hotel A (Luxury Resorts)          tenant_id: hotel-luxury-001
├─ Owner:   hotel-a-owner@luxury.com
├─ Admin:   hotel-a-admin@luxury.com
├─ Staff:   receptionist1@luxury.com
└─ Customers: john@gmail.com, jane@yahoo.com  (global — no tenant)

Hotel B (Budget Inn)              tenant_id: hotel-budget-001
├─ Owner:   hotel-b-owner@budget.com
└─ Staff:   frontdesk@budget.com
```

### Role Mapping

| Generic Role | Hotel Context |
|---|---|
| owner | Hotel Owner |
| admin | General Manager |
| manager | Department Manager |
| supervisor | Shift Supervisor |
| coordinator | Guest Relations |
| staff | Receptionist |
| customer | Hotel Guest |

### Step-by-Step Setup

**1. Deploy:**
```bash
APP_NAME=hotel-manager ENVIRONMENT=prod ./deploy-sam.sh
# or via GitHub Actions: set APP_NAME=hotel-manager in Variables
```

**2. Create master user:**
```bash
API_URL="https://xxx.execute-api.region.amazonaws.com/prod"

curl -X POST $API_URL/auth/register-master \
  -H "Content-Type: application/json" \
  -d '{
    "secret_key": "YOUR_MASTER_SECRET_KEY",
    "email": "admin@yourcompany.com",
    "password": "SecurePass123!",
    "first_name": "System",
    "last_name": "Administrator"
  }'
```

**3. Login as master:**
```bash
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourcompany.com", "password": "SecurePass123!"}'

MASTER_TOKEN="eyJhbGci..."
```

**4. Create Hotel A owner:**
```bash
curl -X POST $API_URL/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -d '{
    "email": "hotel-a-owner@luxury.com",
    "password": "SecurePass456!",
    "first_name": "Hotel A",
    "last_name": "Owner",
    "role": "owner",
    "tenant_id": "hotel-luxury-001"
  }'
```

**5. Hotel A owner creates staff:**
```bash
HOTEL_A_TOKEN="..."   # login as hotel-a-owner first

curl -X POST $API_URL/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HOTEL_A_TOKEN" \
  -d '{
    "email": "receptionist1@luxury.com",
    "password": "Staff123!",
    "first_name": "Alice",
    "last_name": "Smith",
    "role": "staff"
  }'
```

**6. Guests register themselves:**
```bash
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@gmail.com",
    "password": "Customer123!",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+19876543210"
  }'
```

### Data Isolation Result

| Who | Can see | Cannot see |
|---|---|---|
| Hotel A staff | All Hotel A data | Hotel B data |
| Hotel B staff | All Hotel B data | Hotel A data |
| Guest John | His own bookings at any hotel | Other guests' data |

---

## 2. Restaurant POS System

### Scenario

Multi-location restaurant chain with separate data per location.

### Deployment

```bash
APP_NAME=restaurant-pos ENVIRONMENT=prod ./deploy-sam.sh
```

### Role Mapping

| Generic Role | Restaurant Context |
|---|---|
| owner | Restaurant Chain Owner |
| admin | Regional Manager |
| manager | Location Manager |
| supervisor | Shift Lead |
| coordinator | Event Coordinator |
| staff | Server / Kitchen Staff |
| customer | Online Ordering User |

### Example: Create a Location

```bash
# Master creates owner for Location 1
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "location1-manager@restaurant.com",
    "password": "Secure123!",
    "first_name": "Location 1",
    "last_name": "Manager",
    "role": "owner",
    "tenant_id": "restaurant-loc-001"
  }'
```

---

## 3. Gym / Fitness Platform

### Scenario

Fitness platform with trainers, members, and multiple gym locations.

### Deployment

```bash
APP_NAME=gymflow ENVIRONMENT=prod ./deploy-sam.sh
```

### Role Mapping

| Generic Role | Gym Context |
|---|---|
| owner | Gym Owner |
| admin | Gym Manager |
| manager | Head Trainer |
| supervisor | Senior Trainer |
| coordinator | Class Coordinator |
| staff | Trainer |
| customer | Gym Member |

### Example Workflow

```bash
# Master creates gym owner
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "gym-owner@fitness.com",
    "password": "Secure123!",
    "first_name": "Gym",
    "last_name": "Owner",
    "role": "owner",
    "tenant_id": "gym-downtown-001"
  }'

# Owner creates trainers
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $GYM_OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trainer@fitness.com",
    "password": "Trainer123!",
    "first_name": "John",
    "last_name": "Trainer",
    "role": "staff"
  }'

# Members self-register
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "member@gmail.com",
    "password": "Member123!",
    "first_name": "Jane",
    "last_name": "Member",
    "phone": "+1234567890"
  }'
```

---

## 4. SaaS Multi-Tenant Platform

### Scenario

B2B SaaS where each company is a tenant with its own isolated users.

### Deployment

```bash
APP_NAME=saas-platform ENVIRONMENT=prod ./deploy-sam.sh
```

### Structure

```
Master (Platform Owner — You)
├─ Company A  tenant_id: company-a-001
│   ├─ owner  (Company Admin)
│   ├─ manager (Team Lead)
│   └─ staff  (Team Members)
└─ Company B  tenant_id: company-b-002
    ├─ owner
    └─ staff
```

### Onboarding a New Company

```bash
# Master creates company owner
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@companyA.com",
    "password": "CompanyA123!",
    "first_name": "Company A",
    "last_name": "Administrator",
    "role": "owner",
    "tenant_id": "company-a-001"
  }'

# Company owner creates their team
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $COMPANY_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teamlead@companyA.com",
    "password": "TeamLead123!",
    "first_name": "John",
    "last_name": "TeamLead",
    "role": "manager"
  }'
```

---

## 5. E-Learning Platform

### Scenario

Online courses with instructors and students.

### Deployment

```bash
APP_NAME=elearning ENVIRONMENT=prod ./deploy-sam.sh
```

### Role Mapping

| Generic Role | E-Learning Context |
|---|---|
| owner | Platform Admin |
| admin | Academic Director |
| manager | Course Coordinator |
| supervisor | Department Head |
| coordinator | Teaching Assistant |
| staff | Instructor |
| customer | Student |

### Example: Create an Instructor

```bash
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "instructor@university.edu",
    "password": "Instructor123!",
    "first_name": "Prof",
    "last_name": "Smith",
    "role": "staff"
  }'

# Student self-registers
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@email.com",
    "password": "Student123!",
    "first_name": "Alice",
    "last_name": "Student",
    "phone": "+1234567890"
  }'
```

---

## 6. Healthcare Clinic System

### Scenario

Medical clinic with doctors, nurses, and patients.

### Deployment

```bash
APP_NAME=clinic-system ENVIRONMENT=prod ./deploy-sam.sh
```

### Role Mapping

| Generic Role | Clinic Context |
|---|---|
| owner | Clinic Director |
| admin | Office Manager |
| manager | Head Physician |
| supervisor | Senior Nurse |
| coordinator | Patient Coordinator |
| staff | Medical Staff |
| customer | Patient |

> **HIPAA Note:** For healthcare deployments, ensure DynamoDB encryption at rest is enabled,
> audit logging is active, a BAA is in place with AWS, and you conduct regular security audits.

### Example Workflow

```bash
# Create doctor
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $CLINIC_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@clinic.com",
    "password": "Doctor123!",
    "first_name": "Dr. John",
    "last_name": "Smith",
    "role": "manager"
  }'
```

---

## Common Workflows

### Promote a User

```bash
# Find the user's ID
curl -X GET "$API_URL/users" -H "Authorization: Bearer $ADMIN_TOKEN"

# Change their role
curl -X PUT "$API_URL/users/{user_id}/role" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

### List Users (Tenant-Filtered)

```bash
# Admin sees only their tenant's users
curl -X GET "$API_URL/users" -H "Authorization: Bearer $ADMIN_TOKEN"

# Master sees ALL users across all tenants
curl -X GET "$API_URL/users" -H "Authorization: Bearer $MASTER_TOKEN"
```

### Delete a User (Master Only)

```bash
curl -X DELETE "$API_URL/users/{user_id}" -H "Authorization: Bearer $MASTER_TOKEN"
```

---

## Testing Tenant Isolation

```bash
# 1. Create two tenants (as master)
curl -X POST $API_URL/users -H "Authorization: Bearer $MASTER_TOKEN" \
  -d '{..."tenant_id": "tenant-a"...}'
curl -X POST $API_URL/users -H "Authorization: Bearer $MASTER_TOKEN" \
  -d '{..."tenant_id": "tenant-b"...}'

# 2. Login as Tenant A admin, try to access a Tenant B user
curl -X GET "$API_URL/users/{tenant_b_user_id}" \
  -H "Authorization: Bearer $TENANT_A_TOKEN"
# Expected: 403 Forbidden

# 3. Customer can always see their own profile
curl -X GET "$API_URL/auth/me" -H "Authorization: Bearer $CUSTOMER_TOKEN"
# Expected: their own data regardless of which tenants they interacted with
```

---

## Deployment Checklist

For each new white-label instance:

- [ ] Choose `APP_NAME` (lowercase, alphanumeric + hyphens)
- [ ] Set `APP_NAME` in GitHub Variables (or env var for manual deploy)
- [ ] Deploy to `dev` first and smoke-test
- [ ] Create master user
- [ ] Create at least one owner (with a `tenant_id`)
- [ ] Verify tenant isolation (cross-tenant 403s)
- [ ] Deploy to `staging` → run integration tests
- [ ] Deploy to `production`
- [ ] Configure custom domain (if applicable)
- [ ] Set up CloudWatch alarms
- [ ] Document the `tenant_id` naming convention for this client
