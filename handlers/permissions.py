"""
Resource Permission Handlers
"""
import json
from utils import (
    AppSettingsDB,
    success_response,
    error_response,
    validation_error_response,
)
from middleware import require_auth
from config.permissions import DEFAULT_RESOURCE_PERMISSIONS, VALID_ROLES


@require_auth(resource='permissions', operation='read')
def get_all_permissions(event, context):
    """GET /permissions"""
    try:
        configs = AppSettingsDB.get_all_resource_configs()
        return success_response(data={
            'resources':      configs,
            'default_config': DEFAULT_RESOURCE_PERMISSIONS,
        })
    except Exception as e:
        print(f"Get permissions error: {e}")
        return error_response("Failed to get permissions", status_code=500)


@require_auth(resource='permissions', operation='read')
def get_resource_permissions(event, context):
    """GET /permissions/{resource}"""
    try:
        resource = (event.get('pathParameters') or {}).get('resource')
        config = AppSettingsDB.get_resource_config(resource)
        if config is None:
            return error_response(
                f"No permission config found for resource '{resource}'. "
                "Call POST /permissions/seed to initialise defaults.",
                status_code=404,
                error_code="NOT_FOUND",
            )
        return success_response(data={'resource': resource, **config})
    except Exception as e:
        print(f"Get resource permissions error: {e}")
        return error_response("Failed to get resource permissions", status_code=500)


@require_auth(resource='permissions', operation='update')
def update_resource_permissions(event, context):
    """
    PUT /permissions/{resource}

    Full replace of the operations map for a resource, with optional metadata.
    Existing created_at, display_name, and description are preserved if not provided.
    Cache is automatically cleared on update.

    Body:
    {
        "operations": {
            "create": ["owner", "admin"],
            "read":   ["owner", "admin", "manager"]
        },
        "display_name": "...",   // optional
        "description":  "..."    // optional
    }
    """
    try:
        resource = (event.get('pathParameters') or {}).get('resource')
        if not resource:
            return error_response("Resource name is required", status_code=400)

        body = json.loads(event.get('body', '{}'))
        if not isinstance(body, dict) or not body:
            return validation_error_response(
                "Body must be a non-empty JSON object"
            )

        operations = body.get('operations')
        if not isinstance(operations, dict) or not operations:
            return validation_error_response(
                "Body must include 'operations': a non-empty map of {operation: [roles]}"
            )

        display_name = body.get('display_name')
        description  = body.get('description')

        errors = {}
        validated_ops = {}
        valid_non_master = [r for r in VALID_ROLES if r != 'master']

        for op, roles in operations.items():
            if not isinstance(op, str) or not op:
                errors[str(op)] = "Operation name must be a non-empty string"
                continue
            if not isinstance(roles, list):
                errors[op] = "Value must be a list of role names"
                continue
            invalid = [r for r in roles if r not in valid_non_master]
            if invalid:
                errors[op] = (
                    f"Invalid roles: {', '.join(invalid)}. "
                    "master always has access and cannot be listed."
                )
                continue
            validated_ops[op] = roles

        if errors:
            return validation_error_response("Invalid operations", errors)

        record = AppSettingsDB.set_resource_config(
            resource, validated_ops,
            display_name=display_name,
            description=description,
        )
        return success_response(
            data={'resource': resource, **record},
            message=f"Permissions updated for resource '{resource}'",
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")
    except Exception as e:
        print(f"Update resource permissions error: {e}")
        return error_response("Failed to update resource permissions", status_code=500)


@require_auth(resource='permissions', operation='seed')
def seed_permissions(event, context):
    """
    POST /permissions/seed
    Writes DEFAULT_RESOURCE_PERMISSIONS to DynamoDB. Master only, idempotent.
    Call this after deploying a new resource to initialise its default config.
    """
    try:
        result = AppSettingsDB.seed_default_permissions()
        return success_response(
            data=result,
            message=f"Seeded permissions for {len(result['seeded'])} resources",
        )
    except Exception as e:
        print(f"Seed permissions error: {e}")
        return error_response("Failed to seed permissions", status_code=500)
