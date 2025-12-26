"""
Response Utilities - Comprehensive Response Builder
"""
from typing import Any, Dict, Optional


# ========================================
# Core Response Builders
# ========================================

def success_response(data: Any = None, message: str = "Success", status_code: int = 200, meta: Optional[Dict] = None) -> Dict:
    """
    Create a unified success response

    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code (default: 200)
        meta: Optional metadata (pagination, etc.)

    Returns:
        {
          "success": true,
          "status_code": 200,
          "message": "...",
          "data": {...},
          "error": null,
          "meta": {}
        }
    """
    return {
        'statusCode': status_code,
        'body': {
            'success': True,
            'status_code': status_code,
            'message': message,
            'data': data,
            'error': None,
            'meta': meta or {}
        }
    }


def error_response(message: str, status_code: int = 400, error_code: Optional[str] = None, error_details: Optional[Dict] = None) -> Dict:
    """
    Create a unified error response

    Args:
        message: Error message
        status_code: HTTP status code
        error_code: Optional error code for client handling
        error_details: Optional additional error details

    Returns:
        {
          "success": false,
          "status_code": 400,
          "message": "...",
          "data": null,
          "error": {
            "code": "ERROR_CODE",
            "details": {...}
          },
          "meta": {}
        }
    """
    error_obj = {}
    if error_code:
        error_obj['code'] = error_code
    if error_details:
        error_obj['details'] = error_details

    return {
        'statusCode': status_code,
        'body': {
            'success': False,
            'status_code': status_code,
            'message': message,
            'data': None,
            'error': error_obj if error_obj else None,
            'meta': {}
        }
    }


# ========================================
# Success Response Helpers
# ========================================

def ok_response(data: Any = None, message: str = "Success") -> Dict:
    """200 OK - Standard success response"""
    return success_response(data=data, message=message, status_code=200)


def created_response(data: Any = None, message: str = "Resource created successfully") -> Dict:
    """201 Created - Resource creation success"""
    return success_response(data=data, message=message, status_code=201)


def accepted_response(data: Any = None, message: str = "Request accepted for processing") -> Dict:
    """202 Accepted - Request accepted but not yet processed"""
    return success_response(data=data, message=message, status_code=202)


def no_content_response() -> Dict:
    """204 No Content - Success with no response body"""
    return success_response(data=None, message="Success", status_code=204)


# ========================================
# Client Error Response Helpers (4xx)
# ========================================

def bad_request_response(message: str = "Bad request", details: Optional[Dict] = None) -> Dict:
    """400 Bad Request - Invalid request"""
    return error_response(
        message=message,
        status_code=400,
        error_code='BAD_REQUEST',
        error_details=details
    )


def unauthorized_response(message: str = "Unauthorized - Authentication required") -> Dict:
    """401 Unauthorized - Authentication required"""
    return error_response(
        message=message,
        status_code=401,
        error_code='UNAUTHORIZED'
    )


def forbidden_response(message: str = "Forbidden - You don't have permission to access this resource") -> Dict:
    """403 Forbidden - Permission denied"""
    return error_response(
        message=message,
        status_code=403,
        error_code='FORBIDDEN'
    )


def not_found_response(message: str = "Resource not found") -> Dict:
    """404 Not Found - Resource doesn't exist"""
    return error_response(
        message=message,
        status_code=404,
        error_code='NOT_FOUND'
    )


def method_not_allowed_response(message: str = "Method not allowed") -> Dict:
    """405 Method Not Allowed"""
    return error_response(
        message=message,
        status_code=405,
        error_code='METHOD_NOT_ALLOWED'
    )


def conflict_response(message: str = "Resource conflict", details: Optional[Dict] = None) -> Dict:
    """409 Conflict - Resource already exists or conflicts"""
    return error_response(
        message=message,
        status_code=409,
        error_code='CONFLICT',
        error_details=details
    )


def validation_error_response(message: str = "Validation failed", errors: Optional[Dict] = None) -> Dict:
    """422 Unprocessable Entity - Validation error"""
    return error_response(
        message=message,
        status_code=422,
        error_code='VALIDATION_ERROR',
        error_details=errors
    )


def rate_limit_response(message: str = "Rate limit exceeded - Too many requests") -> Dict:
    """429 Too Many Requests - Rate limit exceeded"""
    return error_response(
        message=message,
        status_code=429,
        error_code='RATE_LIMIT_EXCEEDED'
    )


# ========================================
# Server Error Response Helpers (5xx)
# ========================================

def internal_server_error_response(message: str = "Internal server error", details: Optional[Dict] = None) -> Dict:
    """500 Internal Server Error"""
    return error_response(
        message=message,
        status_code=500,
        error_code='INTERNAL_SERVER_ERROR',
        error_details=details
    )


def service_unavailable_response(message: str = "Service temporarily unavailable") -> Dict:
    """503 Service Unavailable"""
    return error_response(
        message=message,
        status_code=503,
        error_code='SERVICE_UNAVAILABLE'
    )


# ========================================
# Specialized Response Builders
# ========================================

def login_success_response(user: Dict, access_token: str, refresh_token: str, expires_in: int) -> Dict:
    """Specialized login success response"""
    return success_response(
        data={
            'user': {
                'user_id': user.get('user_id'),
                'email': user.get('email'),
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name'),
                'phone': user.get('phone'),
                'role': user.get('role')
            },
            'tokens': {
                'access': access_token,
                'refresh': refresh_token,
                'type': 'Bearer',
                'expires_in': expires_in
            }
        },
        message="Login successful",
        status_code=200
    )


def registration_success_response(user: Dict, message: str = "Registration successful") -> Dict:
    """Specialized registration success response"""
    return created_response(
        data={
            'user_id': user.get('user_id'),
            'email': user.get('email'),
            'first_name': user.get('first_name'),
            'last_name': user.get('last_name'),
            'phone': user.get('phone'),
            'role': user.get('role'),
            'is_verified': user.get('is_verified', False),
            'created_at': user.get('created_at')
        },
        message=message
    )


def paginated_response(items: list, total: int, page: int, page_size: int, message: str = "Success") -> Dict:
    """Response with pagination metadata"""
    total_pages = (total + page_size - 1) // page_size

    return success_response(
        data=items,
        message=message,
        meta={
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
    )
