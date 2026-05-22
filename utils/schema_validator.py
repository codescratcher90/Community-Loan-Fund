"""
Schema-based request body validation.

SchemaField  — declares a single field's rules.
Schema       — collects fields, runs all checks, supports cross-field rules.
@validate_request_body — decorator that validates before the handler runs.

Custom validators
-----------------
A custom_validator may either:
  - return (bool, str | None)  →  (is_valid, error_message)
  - raise ValidationError      →  message taken from the exception
Both styles are handled transparently.

Cross-field validators
----------------------
Pass a list of callables to Schema(cross_field_validators=[...]).
Each callable receives the full validated data dict and should raise
ValidationError if the combination of values is invalid.

  def passwords_match(data):
      if data.get('password') != data.get('confirm_password'):
          raise ValidationError('Passwords do not match',
                                {'confirm_password': 'Must match password'})
"""

from __future__ import annotations
import re
from typing import Any, Callable, Dict, List, Optional, Union

from utils.responses import error_response


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# SchemaField
# ---------------------------------------------------------------------------

class SchemaField:
    """
    Declares validation rules for a single request body field.

    Parameters
    ----------
    field_type   : expected Python type (str, int, bool, list, dict)
    required     : if True and field is absent, validation fails
    nullable     : if True, None is accepted regardless of field_type
    min_length   : minimum string length
    max_length   : maximum string length
    min_value    : minimum numeric value
    max_value    : maximum numeric value
    allowed_values : field must be one of these values
    pattern      : regex the string must fully match
    custom_validator : callable(value) → (bool, str|None) or raises ValidationError
    description  : human-readable description (used in docs / error messages)
    """

    def __init__(
        self,
        field_type: type,
        required: bool = True,
        nullable: bool = False,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        allowed_values: Optional[List[Any]] = None,
        pattern: Optional[str] = None,
        custom_validator: Optional[Callable] = None,
        description: Optional[str] = None,
    ):
        self.field_type       = field_type
        self.required         = required
        self.nullable         = nullable
        self.min_length       = min_length
        self.max_length       = max_length
        self.min_value        = min_value
        self.max_value        = max_value
        self.allowed_values   = allowed_values
        self.pattern          = pattern
        self.custom_validator = custom_validator
        self.description      = description

    def validate(self, field_name: str, value: Any) -> None:
        """Validate value against all rules for this field. Raises ValidationError on failure."""

        # Null check
        if value is None:
            if self.nullable:
                return
            raise ValidationError(
                f"Field '{field_name}' cannot be null",
                {field_name: "This field cannot be null"},
            )

        # Type check
        if not isinstance(value, self.field_type):
            raise ValidationError(
                f"Invalid type for field '{field_name}'",
                {field_name: f"Expected {self.field_type.__name__}, got {type(value).__name__}"},
            )

        # String rules
        if isinstance(value, str):
            if self.min_length is not None and len(value) < self.min_length:
                raise ValidationError(
                    f"Field '{field_name}' is too short",
                    {field_name: f"Minimum length is {self.min_length} characters"},
                )
            if self.max_length is not None and len(value) > self.max_length:
                raise ValidationError(
                    f"Field '{field_name}' is too long",
                    {field_name: f"Maximum length is {self.max_length} characters"},
                )

        # Numeric rules
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if self.min_value is not None and value < self.min_value:
                raise ValidationError(
                    f"Field '{field_name}' value is too small",
                    {field_name: f"Minimum value is {self.min_value}"},
                )
            if self.max_value is not None and value > self.max_value:
                raise ValidationError(
                    f"Field '{field_name}' value is too large",
                    {field_name: f"Maximum value is {self.max_value}"},
                )

        # Allowed values
        if self.allowed_values is not None and value not in self.allowed_values:
            raise ValidationError(
                f"Invalid value for field '{field_name}'",
                {field_name: f"Allowed values: {', '.join(map(str, self.allowed_values))}"},
            )

        # Regex pattern
        if self.pattern is not None and isinstance(value, str):
            if not re.fullmatch(self.pattern, value):
                raise ValidationError(
                    f"Field '{field_name}' does not match required pattern",
                    {field_name: f"Value must match pattern: {self.pattern}"},
                )

        # Custom validator — accepts both (bool, str) tuples and raised exceptions
        if self.custom_validator is not None:
            try:
                result = self.custom_validator(value)
            except ValidationError:
                raise
            except Exception as exc:
                raise ValidationError(
                    f"Validation failed for '{field_name}'",
                    {field_name: str(exc)},
                ) from exc

            # Handle (bool, str | None) return style
            if isinstance(result, tuple):
                is_valid, error_msg = result
                if not is_valid:
                    raise ValidationError(
                        f"Validation failed for '{field_name}'",
                        {field_name: error_msg or f"Invalid value for {field_name}"},
                    )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class Schema:
    """
    Collects SchemaField declarations for one request body shape.

    Parameters
    ----------
    fields                : field name → SchemaField
    strict                : reject unknown fields when True (default)
    cross_field_validators: list of callables run after per-field validation;
                            each receives the full data dict and raises
                            ValidationError if the combination is invalid
    """

    def __init__(
        self,
        fields: Dict[str, SchemaField],
        strict: bool = True,
        cross_field_validators: Optional[List[Callable[[Dict], None]]] = None,
    ):
        self.fields                 = fields
        self.strict                 = strict
        self.cross_field_validators = cross_field_validators or []

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against the schema.
        Returns validated data unchanged on success.
        Raises ValidationError with a details dict on failure.
        Collects ALL errors before raising (no early exit).
        """
        if not isinstance(data, dict):
            raise ValidationError(
                "Request body must be a JSON object",
                {"body": f"Expected object, got {type(data).__name__}"},
            )

        errors: Dict[str, str] = {}

        # Missing required fields
        for field_name, field_schema in self.fields.items():
            if field_schema.required and field_name not in data:
                errors[field_name] = "This field is required"

        # Unknown fields (strict mode)
        if self.strict:
            for field_name in data:
                if field_name not in self.fields:
                    errors[field_name] = "This field is not allowed"

        # Per-field validation (only for fields that are present)
        for field_name, value in data.items():
            if field_name not in self.fields:
                continue
            field_schema = self.fields[field_name]

            # Skip custom/type checks when field is absent-but-optional (already handled above)
            if value is None and not field_schema.nullable and not field_schema.required:
                continue

            try:
                field_schema.validate(field_name, value)
            except ValidationError as exc:
                errors.update(exc.details)

        if errors:
            raise ValidationError("Validation failed", errors)

        # Cross-field validation (only runs when per-field passes)
        for validator in self.cross_field_validators:
            try:
                validator(data)
            except ValidationError as exc:
                raise ValidationError(exc.message, exc.details) from exc

        return data


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def validate_request_body(schema: Schema):
    """
    Decorator: parse and validate the request body before the handler runs.

    Usage
    -----
        @validate_request_body(registration_schema)
        def register(event, context):
            body = json.loads(event['body'])   # already validated
            ...
    """
    import json
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            try:
                body = json.loads(event.get('body') or '{}')
            except json.JSONDecodeError:
                return error_response(
                    "Invalid JSON in request body",
                    status_code=400,
                    error_code="INVALID_JSON",
                )

            try:
                schema.validate(body)
            except ValidationError as exc:
                return error_response(
                    exc.message,
                    status_code=422,
                    error_code="VALIDATION_ERROR",
                    error_details=exc.details,
                )

            return func(event, context)

        return wrapper
    return decorator
