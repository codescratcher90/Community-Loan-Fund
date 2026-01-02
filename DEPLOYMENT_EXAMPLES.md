# Real-World Deployment Examples 🚀

This guide shows **complete end-to-end examples** of deploying the Basic-Auth system for different use cases.

---

## Table of Contents

1. [Hotel Management System](#1-hotel-management-system)
2. [Restaurant POS System](#2-restaurant-pos-system)
3. [Gym/Fitness Platform](#3-gymfitness-platform)
4. [SaaS Multi-Tenant Platform](#4-saas-multi-tenant-platform)
5. [E-Learning Platform](#5-e-learning-platform)
6. [Healthcare Clinic System](#6-healthcare-clinic-system)

---

## 1. Hotel Management System

### Scenario
You're building a hotel management system for multiple hotel chains. Each hotel needs to manage staff (receptionists, managers) and guests (customers).

### Architecture

```
System Master (You)
└─ Creates owners for each hotel

Hotel A (Luxury Resorts)
├─ Owner: hotel-a-owner@luxury.com
├─ Admin: hotel-a-admin@luxury.com
├─ Staff: receptionist1@luxury.com, receptionist2@luxury.com
└─ Customers: john@gmail.com, jane@yahoo.com (can stay at multiple hotels)

Hotel B (Budget Inn)
├─ Owner: hotel-b-owner@budget.com
├─ Admin: hotel-b-admin@budget.com
├─ Staff: frontdesk@budget.com
└─ Customers: mike@gmail.com, sarah@hotmail.com
```

### Deployment Steps

**1. Deploy the System:**

```bash
# Set app name for hotel system
APP_NAME=hotel-manager ENVIRONMENT=prod ./deploy-sam.sh
```

Or via GitHub Actions:
- Settings → Actions → Variables → Add `APP_NAME=hotel-manager`
- Actions → Deploy to Production → Run workflow

**2. Create Master User:**

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

**3. Login as Master:**

```bash
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourcompany.com",
    "password": "SecurePass123!"
  }'

# Save the access_token from response
MASTER_TOKEN="eyJhbGci..."
```

**4. Create Owner for Hotel A:**

```bash
curl -X POST $API_URL/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -d '{
    "email": "hotel-a-owner@luxury.com",
    "password": "SecurePass456!",
    "first_name": "Hotel A",
    "last_name": "Owner",
    "phone": "+12345678901",
    "role": "owner",
    "tenant_id": "hotel-luxury-001"
  }'
```

**5. Create Owner for Hotel B:**

```bash
curl -X POST $API_URL/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -d '{
    "email": "hotel-b-owner@budget.com",
    "password": "SecurePass789!",
    "first_name": "Hotel B",
    "last_name": "Owner",
    "phone": "+12345678902",
    "role": "owner",
    "tenant_id": "hotel-budget-001"
  }'
```

**6. Hotel A Owner Creates Staff:**

```bash
# Login as Hotel A Owner
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "hotel-a-owner@luxury.com",
    "password": "SecurePass456!"
  }'

HOTEL_A_TOKEN="eyJhbGci..."

# Create receptionist
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

**7. Customers Register:**

```bash
# Customer registers (can book at any hotel)
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

### Data Isolation

**Hotel A Staff can see:**
- ✅ All Hotel A bookings
- ✅ All Hotel A staff
- ❌ Hotel B bookings (isolated)
- ❌ Hotel B staff (isolated)

**Customer John can see:**
- ✅ His booking at Hotel A
- ✅ His booking at Hotel B
- ✅ All his bookings across all hotels
- ❌ Other customers' bookings

---

## 2. Restaurant POS System

### Scenario
Multi-location restaurant chain with separate data for each location.

### Deployment

```bash
APP_NAME=restaurant-pos ENVIRONMENT=prod ./deploy-sam.sh
```

### Role Structure

```
Master (System Administrator)
└─ Owner (Restaurant Chain Owner)
    ├─ Admin (Regional Manager)
    │   ├─ Manager (Location Manager)
    │   │   ├─ Staff (Servers, Kitchen Staff)
    │   │   └─ Customer (Online Ordering Users)
```

### Example: Create Location

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

## 3. Gym/Fitness Platform

### Scenario
Fitness platform with trainers, members, and multiple gym locations.

### Deployment

```bash
APP_NAME=gymflow ENVIRONMENT=prod ./deploy-sam.sh
```

### Role Mapping

- **Owner** → Gym Owner
- **Admin** → Gym Manager
- **Manager** → Head Trainer
- **Supervisor** → Senior Trainer
- **Coordinator** → Class Coordinator
- **Staff** → Trainer
- **Customer** → Gym Member

### Example Workflow

```bash
# Create gym owner
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

# Members register as customers
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
B2B SaaS platform where each company is a tenant with their own users.

### Deployment

```bash
APP_NAME=saas-platform ENVIRONMENT=prod ./deploy-sam.sh
```

### Structure

```
Master (Platform Owner - You)
└─ Company A (tenant_id: company-a-001)
    ├─ Owner (Company Admin)
    ├─ Manager (Team Lead)
    └─ Staff (Team Members)
└─ Company B (tenant_id: company-b-002)
    ├─ Owner (Company Admin)
    ├─ Manager (Team Lead)
    └─ Staff (Team Members)
```

### Onboarding New Company

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

- **Owner** → Platform Admin
- **Admin** → Academic Director
- **Manager** → Course Coordinator
- **Supervisor** → Department Head
- **Coordinator** → Teaching Assistant
- **Staff** → Instructor
- **Customer** → Student

### Example: Course Setup

```bash
# Create instructor
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

# Student registers
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

- **Owner** → Clinic Director
- **Admin** → Office Manager
- **Manager** → Head Physician
- **Supervisor** → Senior Nurse
- **Coordinator** → Patient Coordinator
- **Staff** → Medical Staff
- **Customer** → Patient

### HIPAA Compliance Note

⚠️ **Important:** For healthcare, ensure:
- All data encrypted at rest (DynamoDB encryption)
- SSL/TLS for API (API Gateway default)
- Audit logging enabled
- BAA with AWS
- Regular security audits

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

# Patient registers
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@email.com",
    "password": "Patient123!",
    "first_name": "Jane",
    "last_name": "Doe",
    "phone": "+1234567890"
  }'
```

---

## Common Workflows

### Promote User Role

```bash
# Get user ID first
curl -X GET "$API_URL/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Promote user
curl -X PUT "$API_URL/users/{user_id}/role" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }'
```

### List All Users (Tenant-Filtered)

```bash
# Admin sees only their tenant's users
curl -X GET "$API_URL/users?limit=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Master sees ALL users across all tenants
curl -X GET "$API_URL/users?limit=100" \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

### Delete User (Master Only)

```bash
curl -X DELETE "$API_URL/users/{user_id}" \
  -H "Authorization: Bearer $MASTER_TOKEN"
```

---

## Testing Tenant Isolation

### Verify Isolation Works

**1. Create two tenants:**
```bash
# Tenant A
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -d '{...tenant_id: "tenant-a"...}'

# Tenant B
curl -X POST $API_URL/users \
  -H "Authorization: Bearer $MASTER_TOKEN" \
  -d '{...tenant_id: "tenant-b"...}'
```

**2. Try to access cross-tenant:**
```bash
# Login as Tenant A admin
# Try to access Tenant B user → Should get 403 Forbidden
curl -X GET "$API_URL/users/{tenant_b_user_id}" \
  -H "Authorization: Bearer $TENANT_A_TOKEN"
# Expected: 403 Forbidden
```

**3. Verify customer access:**
```bash
# Customer books with Tenant A
# Customer books with Tenant B
# Customer can see both bookings
curl -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"
# Expected: Shows all their data across tenants
```

---

## Deployment Checklist

For each new deployment:

- [ ] Choose appropriate `APP_NAME`
- [ ] Set GitHub variable or environment variable
- [ ] Deploy to dev first
- [ ] Create master user
- [ ] Create test owner
- [ ] Test tenant isolation
- [ ] Test customer functionality
- [ ] Deploy to production
- [ ] Update DNS (if using custom domain)
- [ ] Configure monitoring
- [ ] Set up backups

---

## Best Practices

1. **Naming Conventions:**
   - Use descriptive tenant IDs: `hotel-luxury-001`, not `tenant1`
   - Use consistent email formats: `role@tenant.com`

2. **Security:**
   - Rotate master secret regularly
   - Use strong passwords
   - Enable MFA for master/owner accounts
   - Audit access logs

3. **Scalability:**
   - Use pagination for large user lists
   - Index frequently queried fields
   - Monitor DynamoDB capacity
   - Use caching for read-heavy workloads

4. **Testing:**
   - Always test in dev first
   - Verify tenant isolation
   - Test all role permissions
   - Load test before production

---

## Support

- 📖 Main docs: [README.md](README.md)
- 🚀 GitHub Actions: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)
- 🏷️ APP_NAME guide: [GITHUB_ACTIONS_APP_NAME.md](GITHUB_ACTIONS_APP_NAME.md)
- 🎭 Role hierarchy: See README.md "Role Hierarchy" section
