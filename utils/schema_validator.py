"""
Schema-based validation utility for API request bodies.
Ensures no extra fields and no missing required fields.
"""

from typing import Any, Dict, List, Optional, Union
from utils.responses import error_response


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SchemaField:
    """Represents a field in a schema"""

    def __init__(
        self,
        field_type: type,
        required: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        allowed_values: Optional[List[Any]] = None,
        pattern: Optional[str] = None,
        custom_validator: Optional[callable] = None,
        description: Optional[str] = None
    ):
        self.field_type = field_type
        self.required = required
        self.min_length = min_length
        self.max_length = max_length
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = allowed_values
        self.pattern = pattern
        self.custom_validator = custom_validator
        self.description = description

    def validate(self, field_name: str, value: Any) -> None:
        """Validate a field value against the schema"""
        # Type validation
        if not isinstance(value, self.field_type):
            raise ValidationError(
                f"Invalid type for field '{field_name}'",
                {field_name: f"Expected {self.field_type.__name__}, got {type(value).__name__}"}
            )

        # String length validation
        if isinstance(value, str):
            if self.min_length is not None and len(value) < self.min_length:
                raise ValidationError(
                    f"Field '{field_name}' is too short",
                    {field_name: f"Minimum length is {self.min_length} characters"}
                )
            if self.max_length is not None and len(value) > self.max_length:
                raise ValidationError(
                    f"Field '{field_name}' is too long",
                    {field_name: f"Maximum length is {self.max_length} characters"}
                )

        # Numeric value validation
        if isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                raise ValidationError(
                    f"Field '{field_name}' value is too small",
                    {field_name: f"Minimum value is {self.min_value}"}
                )
            if self.max_value is not None and value > self.max_value:
                raise ValidationError(
                    f"Field '{field_name}' value is too large",
                    {field_name: f"Maximum value is {self.max_value}"}
                )

        # Allowed values validation
        if self.allowed_values is not None and value not in self.allowed_values:
            raise ValidationError(
                f"Invalid value for field '{field_name}'",
                {field_name: f"Allowed values are: {', '.join(map(str, self.allowed_values))}"}
            )

        # Pattern validation
        if self.pattern is not None and isinstance(value, str):
            import re
            if not re.match(self.pattern, value):
                raise ValidationError(
                    f"Field '{field_name}' does not match required pattern",
                    {field_name: f"Value must match pattern: {self.pattern}"}
                )

        # Custom validator
        if self.custom_validator is not None:
            try:
                self.custom_validator(value)
            except Exception as e:
                raise ValidationError(
                    f"Custom validation failed for field '{field_name}'",
                    {field_name: str(e)}
                )


class Schema:
    """Represents a request body schema"""

    def __init__(self, fields: Dict[str, SchemaField], strict: bool = True):
        """
        Initialize schema

        Args:
            fields: Dictionary mapping field names to SchemaField objects
            strict: If True, reject requests with extra fields not in schema
        """
        self.fields = fields
        self.strict = strict

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate request data against schema

        Args:
            data: Request body data to validate

        Returns:
            Validated data (same as input if validation passes)

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError(
                "Request body must be a JSON object",
                {"body": "Expected object, got " + type(data).__name__}
            )

        errors = {}

        # Check for missing required fields
        for field_name, field_schema in self.fields.items():
            if field_schema.required and field_name not in data:
                errors[field_name] = "This field is required"

        # Check for extra fields (if strict mode)
        if self.strict:
            for field_name in data.keys():
                if field_name not in self.fields:
                    errors[field_name] = "This field is not allowed"

        # Validate each field that is present
        for field_name, value in data.items():
            if field_name in self.fields:
                try:
                    self.fields[field_name].validate(field_name, value)
                except ValidationError as e:
                    errors.update(e.details)

        # If there are any errors, raise ValidationError
        if errors:
            raise ValidationError("Validation failed", errors)

        return data


def validate_request_body(schema: Schema):
    """
    Decorator to validate request body against a schema

    Usage:
        @validate_request_body(registration_schema)
        def register(event, context):
            # body is already validated here
            body = json.loads(event['body'])
            ...
    """
    def decorator(func):
        def wrapper(event, context):
            import json

            # Parse request body
            try:
                body = json.loads(event.get('body', '{}'))
            except json.JSONDecodeError:
                return error_response(
                    "Invalid JSON in request body",
                    status_code=400,
                    error_code="INVALID_JSON"
                )

            # Validate against schema
            try:
                schema.validate(body)
            except ValidationError as e:
                return error_response(
                    e.message,
                    status_code=400,
                    error_code="VALIDATION_ERROR",
                    error_details=e.details
                )

            # Call the original function
            return func(event, context)

        return wrapper
    return decorator
