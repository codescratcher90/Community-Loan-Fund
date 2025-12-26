"""
Main Lambda Handler with Internal Routing
"""
import json
import os
import re
from typing import Dict, Any, Optional, Tuple
import bcrypt
import traceback

# Import handlers
from handlers import (
    register,
    register_master,
    verify,
    login,
    refresh,
    logout,
    get_me,
    update_me,
    list_users,
    get_user,
    update_user_role,
    delete_user
)
from utils import error_response

# Load environment variables from .env if running locally
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Route mapping
ROUTES = {
    'POST /auth/register': register,
    'POST /auth/register-master': register_master,
    'POST /auth/verify': verify,
    'POST /auth/login': login,
    'POST /auth/refresh': refresh,
    'POST /auth/logout': logout,
    'GET /auth/me': get_me,
    'PUT /auth/me': update_me,
    'GET /users': list_users,
    'GET /users/{id}': get_user,
    'PUT /users/{id}/role': update_user_role,
    'DELETE /users/{id}': delete_user
}


def match_route(http_method: str, path: str) -> Optional[Tuple[Any, Dict[str, str]]]:
    """
    Match incoming request to a route pattern and extract path parameters

    Args:
        http_method: HTTP method (GET, POST, etc.)
        path: Request path

    Returns:
        Tuple of (handler_function, path_parameters) or None if no match
    """
    for route_pattern, handler in ROUTES.items():
        # Split route pattern into method and path
        pattern_method, pattern_path = route_pattern.split(' ', 1)

        # Check if method matches
        if pattern_method != http_method:
            continue

        # Convert route pattern to regex
        # Replace {param} with named capture groups
        regex_pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern_path)
        regex_pattern = f'^{regex_pattern}$'

        # Try to match the path
        match = re.match(regex_pattern, path)
        if match:
            # Extract path parameters
            path_params = match.groupdict()
            return handler, path_params

    return None


def lambda_handler(event: Dict[str, Any], context):
    print("=== Lambda handler START ===")
    try:
        # Print raw event and context
        print("Incoming event:", json.dumps(event))
        print("Event type:", type(event))
        print("Event keys:", list(event.keys()))
        print("Context:", context)

        # Detect route and HTTP method
        http_method = event.get("httpMethod")
        path = event.get("path")
        route_key = f"{http_method} {path}"
        print(f"Detected route key: {route_key}")

        # 🧩 1. Handle CORS preflight (OPTIONS request)
        if http_method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,PATCH,DELETE",
                },
            }

        # Parse body safely
        body = event.get("body")
        if body:
            if isinstance(body, str):
                try:
                    print("Parsing body JSON string")
                    body = json.loads(body)
                except json.JSONDecodeError:
                    print("Body is not valid JSON — keeping as string")
        print("Parsed body:", body)

        # Environment variables
        secret_key = os.getenv("MASTER_SECRET_KEY")
        print("SECRET_KEY from env:", secret_key)

        # Route matching with path parameters
        route_match = match_route(http_method, path)

        if route_match:
            handler_func, path_params = route_match
            print(f"Found handler for route: {route_key}")
            print(f"Path parameters: {path_params}")

            # Add path parameters to event if not already present
            if 'pathParameters' not in event or event['pathParameters'] is None:
                event['pathParameters'] = {}
            event['pathParameters'].update(path_params)

            # Handler returns {statusCode, body}
            result = handler_func(event, context)
            print("Handler result:", result)

            # Extract statusCode and body from handler response
            status_code = result.get('statusCode', 200)
            response_body = result.get('body', result)

            return {
                "statusCode": status_code,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,PATCH,DELETE"
                },
                "body": json.dumps(response_body)
            }
        else:
            print(f"No handler found for route: {route_key}")
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,PATCH,DELETE"
                },
                "body": json.dumps({
                    "success": False,
                    "message": "Route not found",
                    "data": None,
                    "error": {
                        "code": "ROUTE_NOT_FOUND",
                        "details": {"route": route_key}
                    },
                    "meta": {}
                })
            }

    except Exception as e:
        print("=== EXCEPTION CAUGHT ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,PATCH,DELETE"
            },
            "body": json.dumps({
                "success": False,
                "message": "Internal server error",
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "details": {"error": str(e)}
                },
                "meta": {}
            })
        }

    finally:
        print("=== Lambda handler END ===")


# For local testing
if __name__ == '__main__':
    test_event = {
        'httpMethod': 'POST',
        'path': '/auth/register-master',
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            "secret_key": "ASDasd09324AKJHFAOAQWEPOIWE",
            "email": "admin@test.com",
            "password": "pass1234",
            "first_name": "Admin",
            "last_name": "User"
        }),
        'pathParameters': {},
        'queryStringParameters': {},
        'requestContext': {
            'identity': {
                'sourceIp': '127.0.0.1'
            }
        }
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
