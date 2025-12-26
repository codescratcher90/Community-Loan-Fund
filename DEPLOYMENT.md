# Deployment Guide 🚀

Quick reference guide for deploying Basic Auth API to any AWS account.

## Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured
- [ ] AWS SAM CLI installed
- [ ] Docker installed and running

## Step-by-Step Deployment

### 1️⃣ Configure AWS Credentials

```bash
# Configure your AWS credentials
aws configure

# Enter your credentials:
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region: eu-north-1  (or your preferred region)
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

### 2️⃣ Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Generate secure secrets
openssl rand -base64 32  # Use for JWT_SECRET
openssl rand -base64 32  # Use for REFRESH_TOKEN_SECRET
openssl rand -base64 32  # Use for MASTER_SECRET_KEY

# Or use the Makefile
make generate-secrets
```

**Edit `.env` file:**

```bash
# Required changes:
JWT_SECRET=<paste-generated-secret-1>
REFRESH_TOKEN_SECRET=<paste-generated-secret-2>
MASTER_SECRET_KEY=<paste-generated-secret-3>

# Optional changes:
AWS_REGION=your-preferred-region
DYNAMODB_TABLE_PREFIX=dev
```

### 3️⃣ Deploy

**Option A: Using the deployment script**

```bash
# Deploy to dev
./deploy-sam.sh dev

# Deploy to staging
./deploy-sam.sh staging

# Deploy to production
./deploy-sam.sh prod
```

**Option B: Using Makefile**

```bash
# Deploy to dev (default)
make deploy

# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-prod
```

### 4️⃣ Get Your API URL

After successful deployment, you'll see output like:

```
API Gateway URL: https://xxxxxxxxxx.execute-api.eu-north-1.amazonaws.com/dev/
Lambda Function: arn:aws:lambda:eu-north-1:123456789012:function:dev-basic-auth-api
```

Or retrieve it later with:

```bash
make endpoints ENV=dev
```

### 5️⃣ Test the Deployment

```bash
# Save your API URL
export API_URL="https://xxxxxxxxxx.execute-api.eu-north-1.amazonaws.com/dev"

# Create a master user
curl -X POST $API_URL/auth/register-master \
  -H "Content-Type: application/json" \
  -d '{
    "secret_key": "your-master-secret-key-from-env",
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

# Save the access_token from response
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Get your profile
curl -X GET $API_URL/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

## Deployment to Different AWS Accounts

### Account 1 (Development)

```bash
# Configure credentials for Account 1
aws configure --profile dev-account

# Set AWS_PROFILE
export AWS_PROFILE=dev-account

# Deploy
make deploy ENV=dev
```

### Account 2 (Production)

```bash
# Configure credentials for Account 2
aws configure --profile prod-account

# Set AWS_PROFILE
export AWS_PROFILE=prod-account

# Use production secrets in .env
# Deploy
make deploy ENV=prod
```

## Environment-Specific Configurations

Each environment creates isolated resources:

| Environment | Stack Name | Tables Prefix | Example URL |
|-------------|------------|---------------|-------------|
| dev | basic-auth-dev | dev_* | https://xxx.execute-api.region.amazonaws.com/dev/ |
| staging | basic-auth-staging | staging_* | https://xxx.execute-api.region.amazonaws.com/staging/ |
| prod | basic-auth-prod | prod_* | https://xxx.execute-api.region.amazonaws.com/prod/ |

## Common Commands

```bash
# Validate template
make validate

# Build application
make build

# Deploy
make deploy ENV=dev

# View logs
make logs ENV=dev

# Show endpoints
make endpoints ENV=dev

# Show stack status
make status ENV=dev

# Clean artifacts
make clean

# Destroy stack (⚠️ deletes everything!)
make destroy ENV=dev
```

## Updating an Existing Deployment

```bash
# Make your code changes...

# Build and deploy
make build
make deploy ENV=dev

# Or quick deploy (combines build + deploy)
make quick-deploy ENV=dev
```

## Switching Between AWS Accounts

### Using AWS Profiles

```bash
# List configured profiles
aws configure list-profiles

# Deploy to different accounts
AWS_PROFILE=dev-account make deploy ENV=dev
AWS_PROFILE=prod-account make deploy ENV=prod
```

### Using Environment Variables

```bash
# Account 1
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export AWS_REGION=eu-north-1
make deploy ENV=dev

# Account 2
export AWS_ACCESS_KEY_ID=yyy
export AWS_SECRET_ACCESS_KEY=yyy
export AWS_REGION=us-east-1
make deploy ENV=prod
```

## Monitoring

### View Logs

```bash
# Tail live logs
make logs ENV=dev

# Or use AWS CLI
aws logs tail /aws/lambda/dev-basic-auth-api --follow
```

### CloudWatch Dashboards

1. Go to AWS Console → CloudWatch
2. Create dashboard with metrics:
   - Lambda: Invocations, Errors, Duration
   - API Gateway: 4XX, 5XX, Latency
   - DynamoDB: Read/Write Capacity, Throttles

## Troubleshooting

### Issue: "Stack does not exist"

**Solution:** Deploy first with `make deploy ENV=dev`

### Issue: "Insufficient permissions"

**Solution:** Ensure IAM user has permissions for:
- Lambda (create, update)
- API Gateway (create, update)
- DynamoDB (create tables)
- CloudFormation (create stack)
- IAM (create roles)
- S3 (for SAM artifacts)

### Issue: "Docker not running"

**Solution:**
```bash
# Start Docker
# macOS/Windows: Open Docker Desktop
# Linux: sudo systemctl start docker
```

### Issue: "Template validation failed"

**Solution:**
```bash
make validate
# Fix errors in template.yaml
```

## Security Checklist

Before deploying to production:

- [ ] Changed all secrets in `.env` from default values
- [ ] Used strong secrets (32+ characters, random)
- [ ] Configured CORS in `template.yaml` (not `*` in prod)
- [ ] Set minimum password length to 12+ in `config/settings.py`
- [ ] Configured appropriate rate limits
- [ ] Reviewed IAM permissions (least privilege)
- [ ] Set up CloudWatch alarms
- [ ] Enabled AWS CloudTrail for audit logging
- [ ] Consider using AWS Secrets Manager for secrets

## Cleanup

To delete all resources:

```bash
# Delete specific environment
make destroy ENV=dev

# Or manually
aws cloudformation delete-stack --stack-name basic-auth-dev
```

## Need Help?

- Check the main [README.md](README.md)
- Review AWS SAM documentation: https://docs.aws.amazon.com/serverless-application-model/
- Open an issue on GitHub

---

**Quick Deploy Checklist:**

```bash
1. aws configure                    # Set up credentials
2. cp .env.example .env            # Create environment file
3. make generate-secrets           # Generate secure secrets
4. Edit .env with generated secrets
5. make deploy ENV=dev             # Deploy!
6. make endpoints ENV=dev          # Get API URL
7. Test with curl                  # Verify it works
```

Done! 🎉
