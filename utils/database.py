"""
DynamoDB Database Utilities
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from config import config

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)

# Table references
users_table = dynamodb.Table(config.USERS_TABLE)
refresh_tokens_table = dynamodb.Table(config.REFRESH_TOKENS_TABLE)
verification_codes_table = dynamodb.Table(config.VERIFICATION_CODES_TABLE)
login_attempts_table = dynamodb.Table(config.LOGIN_ATTEMPTS_TABLE)
rate_limits_table = dynamodb.Table(config.RATE_LIMITS_TABLE)


class UserDB:
    """User table operations"""
    
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        users_table.put_item(Item=user_data)
        return user_data
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        response = users_table.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email)
        )
        items = response.get('Items', [])
        return items[0] if items else None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        response = users_table.get_item(Key={'user_id': user_id})
        return response.get('Item')
    
    @staticmethod
    def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user fields"""
        update_expr = "SET " + ", ".join([f"#{k} = :{k}" for k in updates.keys()])
        expr_attr_names = {f"#{k}": k for k in updates.keys()}
        expr_attr_values = {f":{k}": v for k, v in updates.items()}
        
        response = users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
            ReturnValues='ALL_NEW'
        )
        return response.get('Attributes', {})
    
    @staticmethod
    def delete_user(user_id: str) -> bool:
        """Delete a user"""
        users_table.delete_item(Key={'user_id': user_id})
        return True
    
    @staticmethod
    def list_users(limit: int = 100, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List users
        If tenant_id is provided, only return users from that tenant
        If tenant_id is None, return all users (for master)
        """
        if tenant_id:
            # Filter by tenant_id
            response = users_table.scan(
                FilterExpression=Attr('tenant_id').eq(tenant_id),
                Limit=limit
            )
        else:
            # Return all users (master only)
            response = users_table.scan(Limit=limit)

        return response.get('Items', [])

    @staticmethod
    def list_users_by_tenant(tenant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List all users in a specific tenant"""
        response = users_table.scan(
            FilterExpression=Attr('tenant_id').eq(tenant_id),
            Limit=limit
        )
        return response.get('Items', [])

    @staticmethod
    def list_customers(limit: int = 100) -> List[Dict[str, Any]]:
        """List all customer users (external users with no tenant)"""
        response = users_table.scan(
            FilterExpression=Attr('role').eq('customer'),
            Limit=limit
        )
        return response.get('Items', [])
    
    @staticmethod
    def increment_failed_attempts(user_id: str) -> int:
        """Increment failed login attempts"""
        response = users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET failed_login_attempts = if_not_exists(failed_login_attempts, :zero) + :inc',
            ExpressionAttributeValues={':inc': 1, ':zero': 0},
            ReturnValues='ALL_NEW'
        )
        return response['Attributes']['failed_login_attempts']
    
    @staticmethod
    def reset_failed_attempts(user_id: str):
        """Reset failed login attempts"""
        users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET failed_login_attempts = :zero',
            ExpressionAttributeValues={':zero': 0}
        )
    
    @staticmethod
    def lock_account(user_id: str):
        """Lock user account"""
        users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET is_locked = :locked, locked_at = :now',
            ExpressionAttributeValues={
                ':locked': True,
                ':now': datetime.utcnow().isoformat()
            }
        )


class RefreshTokenDB:
    """Refresh token table operations"""
    
    @staticmethod
    def create_token(token_data: Dict[str, Any]):
        """Store refresh token"""
        refresh_tokens_table.put_item(Item=token_data)
    
    @staticmethod
    def get_token(token: str) -> Optional[Dict[str, Any]]:
        """Get refresh token"""
        response = refresh_tokens_table.get_item(Key={'token': token})
        return response.get('Item')
    
    @staticmethod
    def delete_token(token: str):
        """Delete refresh token (logout)"""
        refresh_tokens_table.delete_item(Key={'token': token})
    
    @staticmethod
    def delete_user_tokens(user_id: str):
        """Delete all tokens for a user"""
        response = refresh_tokens_table.query(
            IndexName='user_id-index',
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        
        for item in response.get('Items', []):
            refresh_tokens_table.delete_item(Key={'token': item['token']})


class VerificationCodeDB:
    """Verification code table operations"""
    
    @staticmethod
    def create_code(code_data: Dict[str, Any]):
        """Store verification code"""
        verification_codes_table.put_item(Item=code_data)
    
    @staticmethod
    def get_code(user_id: str, code_type: str) -> Optional[Dict[str, Any]]:
        """Get verification code"""
        response = verification_codes_table.get_item(
            Key={'user_id': user_id, 'code_type': code_type}
        )
        return response.get('Item')
    
    @staticmethod
    def delete_code(user_id: str, code_type: str):
        """Delete verification code"""
        verification_codes_table.delete_item(
            Key={'user_id': user_id, 'code_type': code_type}
        )
    
    @staticmethod
    def verify_code(user_id: str, code_type: str, code: str) -> bool:
        """Verify a code"""
        stored_code = VerificationCodeDB.get_code(user_id, code_type)
        
        if not stored_code:
            return False
        
        # Check if code matches
        if stored_code.get('code') != code:
            return False
        
        # Check if expired
        expires_at = datetime.fromisoformat(stored_code.get('expires_at'))
        if datetime.utcnow() > expires_at:
            VerificationCodeDB.delete_code(user_id, code_type)
            return False
        
        # Code is valid, delete it
        VerificationCodeDB.delete_code(user_id, code_type)
        return True


class LoginAttemptDB:
    """Login attempt tracking"""
    
    @staticmethod
    def record_attempt(ip_address: str, email: str, success: bool):
        """Record a login attempt"""
        login_attempts_table.put_item(Item={
            'ip_address': ip_address,
            'timestamp': datetime.utcnow().isoformat(),
            'email': email,
            'success': success
        })
    
    @staticmethod
    def count_recent_attempts(ip_address: str, hours: int = 1) -> int:
        """Count login attempts from IP in last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        response = login_attempts_table.query(
            IndexName='ip_address-timestamp-index',
            KeyConditionExpression=Key('ip_address').eq(ip_address) & 
                                   Key('timestamp').gte(cutoff_time.isoformat())
        )
        
        return len(response.get('Items', []))


class RateLimitDB:
    """Rate limiting operations"""
    
    @staticmethod
    def check_and_increment(key: str, limit: int, window_seconds: int) -> bool:
        """
        Check if rate limit is exceeded and increment counter
        Returns True if request is allowed, False if rate limit exceeded
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        try:
            # Get current count
            response = rate_limits_table.get_item(Key={'limit_key': key})
            item = response.get('Item')
            
            if item:
                # Check if window has expired
                reset_at = datetime.fromisoformat(item['reset_at'])
                if now >= reset_at:
                    # Window expired, reset counter
                    rate_limits_table.put_item(Item={
                        'limit_key': key,
                        'count': 1,
                        'reset_at': (now + timedelta(seconds=window_seconds)).isoformat()
                    })
                    return True
                
                # Check if limit exceeded
                if item['count'] >= limit:
                    return False
                
                # Increment counter
                rate_limits_table.update_item(
                    Key={'limit_key': key},
                    UpdateExpression='SET #count = #count + :inc',
                    ExpressionAttributeNames={'#count': 'count'},
                    ExpressionAttributeValues={':inc': 1}
                )
                return True
            else:
                # First request, create entry
                rate_limits_table.put_item(Item={
                    'limit_key': key,
                    'count': 1,
                    'reset_at': (now + timedelta(seconds=window_seconds)).isoformat()
                })
                return True
                
        except Exception as e:
            print(f"Rate limit check error: {str(e)}")
            # On error, allow the request (fail open)
            return True
    
    @staticmethod
    def reset_limit(key: str):
        """Reset rate limit for a key"""
        rate_limits_table.delete_item(Key={'limit_key': key})
