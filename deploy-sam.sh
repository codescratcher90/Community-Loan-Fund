#!/bin/bash

# ========================================
# SAM Deployment Script
# ========================================
# This script deploys the Basic-Auth API using AWS SAM
# Supports custom app names for multi-tenant deployments

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo " Basic-Auth API Deployment"
echo "======================================"
echo

# ========================================
# Get APP_NAME
# ========================================
if [ -z "$APP_NAME" ]; then
    read -p "Enter application name (default: basic-auth): " APP_NAME
    APP_NAME=${APP_NAME:-basic-auth}
fi

# Validate APP_NAME format (lowercase alphanumeric with hyphens)
if ! [[ "$APP_NAME" =~ ^[a-z0-9][a-z0-9-]*[a-z0-9]$ ]]; then
    echo -e "${RED}Error: APP_NAME must be lowercase alphanumeric with hyphens${NC}"
    echo "Examples: basic-auth, hotel-system, my-app-123"
    exit 1
fi

# ========================================
# Get Environment
# ========================================
if [ -z "$ENVIRONMENT" ]; then
    read -p "Enter environment (dev/staging/prod) [default: dev]: " ENVIRONMENT
    ENVIRONMENT=${ENVIRONMENT:-dev}
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}Error: ENVIRONMENT must be dev, staging, or prod${NC}"
    exit 1
fi

# ========================================
# Load secrets from .env if it exists
# ========================================
if [ -f .env ]; then
    echo -e "${YELLOW}Loading secrets from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${YELLOW}Warning: .env file not found. Using default secrets.${NC}"
    echo "Create a .env file from .env.example for production deployments."
fi

# Set default secrets if not in .env
JWT_SECRET=${JWT_SECRET:-change-this-to-a-long-random-secret-key}
REFRESH_TOKEN_SECRET=${REFRESH_TOKEN_SECRET:-change-this-to-another-long-random-secret-key}
MASTER_SECRET_KEY=${MASTER_SECRET_KEY:-your-super-secret-master-key-here}

# ========================================
# Stack and Resource Names
# ========================================
STACK_NAME="${APP_NAME}-${ENVIRONMENT}"

echo
echo "Deployment Configuration:"
echo "  App Name:    $APP_NAME"
echo "  Environment: $ENVIRONMENT"
echo "  Stack Name:  $STACK_NAME"
echo

# ========================================
# Build
# ========================================
echo -e "${GREEN}Building SAM application...${NC}"
sam build

# ========================================
# Deploy
# ========================================
echo -e "${GREEN}Deploying to AWS...${NC}"
sam deploy \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
    AppName="$APP_NAME" \
    Environment="$ENVIRONMENT" \
    JWTSecret="$JWT_SECRET" \
    RefreshTokenSecret="$REFRESH_TOKEN_SECRET" \
    MasterSecretKey="$MASTER_SECRET_KEY" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --resolve-s3

# ========================================
# Get Outputs
# ========================================
echo
echo -e "${GREEN}Deployment complete!${NC}"
echo
echo "Stack Outputs:"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table

echo
echo -e "${GREEN}Resources created:${NC}"
echo "  - DynamoDB Tables:"
echo "    * ${APP_NAME}-${ENVIRONMENT}-users"
echo "    * ${APP_NAME}-${ENVIRONMENT}-refresh_tokens"
echo "    * ${APP_NAME}-${ENVIRONMENT}-verification_codes"
echo "    * ${APP_NAME}-${ENVIRONMENT}-login_attempts"
echo "    * ${APP_NAME}-${ENVIRONMENT}-rate_limits"
echo
echo "  - Lambda Function: ${APP_NAME}-${ENVIRONMENT}-api"
echo "  - API Gateway: ${APP_NAME}-${ENVIRONMENT}-api"
echo

# Get API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

echo -e "${GREEN}API Endpoint:${NC}"
echo "  $API_URL"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Test the API: curl ${API_URL}auth/register-master"
echo "  2. Create a master user using the MASTER_SECRET_KEY"
echo "  3. Start building your application!"
echo
