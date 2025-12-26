"""
Response Utilities
"""
from typing import Any, Dict, Optional

def success_response(data: Any = None, message: str = "Success", status_code: int = 200, meta: Optional[Dict] = None) -> Dict:
    """
    Create a unified success response
    Format:
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
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
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
    Format:
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
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': {
            'success': False,
            'status_code': status_code,
            'message': message,
            'data': None,
            'error': error_obj if error_obj else None,
            'meta': {}
        }
    }


def unauthorized_response(message: str = "Unauthorized") -> Dict:
    """
    Create an unauthorized (401) response
    """
    return error_response(message, status_code=401, error_code='UNAUTHORIZED')


def forbidden_response(message: str = "Forbidden") -> Dict:
    """
    Create a forbidden (403) response
    """
    return error_response(message, status_code=403, error_code='FORBIDDEN')


def not_found_response(message: str = "Not found") -> Dict:
    """
    Create a not found (404) response
    """
    return error_response(message, status_code=404, error_code='NOT_FOUND')


def rate_limit_response(message: str = "Rate limit exceeded") -> Dict:
    """
    Create a rate limit (429) response
    """
    return error_response(message, status_code=429, error_code='RATE_LIMIT_EXCEEDED')


def validation_error_response(message: str, errors: Optional[Dict] = None) -> Dict:
    """
    Create a validation error (422) response
    """
    return error_response(
        message=message,
        status_code=422,
        error_code='VALIDATION_ERROR',
        error_details=errors
    )
