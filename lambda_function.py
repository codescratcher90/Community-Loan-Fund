"""
Main Lambda Handler with Internal Routing
"""
import json
import os
from typing import Dict, Any
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

        # Route handling
        handler_func = ROUTES.get(route_key)
        if handler_func:
            print(f"Found handler for route: {route_key}")
            # Handler returns {statusCode, body}
            result = handler_func(event, context)
            print("Handler result:", result)

            # Extract statusCode and body from handler response
            status_code = result.get('statusCode', 200)
            response_body = result.get('body', result)

            return {
                "statusCode": status_code,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(response_body)
            }
        else:
            print(f"No handler found for route: {route_key}")
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
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
            "headers": {"Content-Type": "application/json"},
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
