"""
Input validation and sanitization utilities for the API.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# Allowed characters for string inputs
SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\s\.\,]+$')

# Maximum input lengths
MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000
MAX_CONFIG_NAME_LENGTH = 100


def sanitize_string(value: str, max_length: int = MAX_NAME_LENGTH) -> str:
    """
    Sanitize a string input by removing potentially dangerous characters.

    Args:
        value: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)

    # Trim to max length
    value = value[:max_length]

    # Remove null bytes and control characters (except newline, tab)
    value = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', value)

    return value.strip()


def sanitize_name(name: str) -> str:
    """
    Sanitize a name field (config name, scenario name, etc.).

    Args:
        name: Input name

    Returns:
        Sanitized name
    """
    name = sanitize_string(name, MAX_NAME_LENGTH)

    # Only allow alphanumeric, underscores, hyphens, spaces, dots, commas
    if not SAFE_STRING_PATTERN.match(name):
        # Replace invalid characters with underscores
        name = re.sub(r'[^\w\-\s\.\,]', '_', name)
        logger.warning(f"Name contained invalid characters, sanitized to: {name}")

    return name


def validate_positive_number(value: Any, field_name: str, allow_zero: bool = False) -> float:
    """
    Validate that a value is a positive number.

    Args:
        value: Value to validate
        field_name: Field name for error messages
        allow_zero: Whether to allow zero

    Returns:
        Validated float value

    Raises:
        ValueError: If validation fails
    """
    try:
        num = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid {field_name}: must be a number") from e

    if allow_zero:
        if num < 0:
            raise ValueError(f"Invalid {field_name}: must be >= 0")
    else:
        if num <= 0:
            raise ValueError(f"Invalid {field_name}: must be > 0")

    return num


def validate_percentage(value: Any, field_name: str) -> float:
    """
    Validate that a value is a valid percentage (0-1 or 0-100).

    Args:
        value: Value to validate
        field_name: Field name for error messages

    Returns:
        Validated float value (0-1 range)

    Raises:
        ValueError: If validation fails
    """
    try:
        num = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid {field_name}: must be a number") from e

    # Handle both 0-1 and 0-100 ranges
    if num > 1:
        num = num / 100.0

    if num < 0 or num > 1:
        raise ValueError(f"Invalid {field_name}: must be between 0 and 1 (or 0-100)")

    return num


def validate_scenario_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize scenario input data.

    Args:
        data: Raw scenario input data

    Returns:
        Validated and sanitized data

    Raises:
        ValueError: If validation fails
    """
    validated = {}

    # Validate name
    if "name" in data and data["name"]:
        validated["name"] = sanitize_name(str(data["name"]))

    # Validate target_tpa
    if "target_tpa" in data:
        validated["target_tpa"] = validate_positive_number(
            data["target_tpa"], "target_tpa"
        )

    # Validate equipment configuration
    if "equipment" in data and isinstance(data["equipment"], dict):
        validated["equipment"] = {}
        equipment = data["equipment"]

        if "reactors_total" in equipment:
            validated["equipment"]["reactors_total"] = int(
                validate_positive_number(
                    equipment["reactors_total"], "reactors_total", allow_zero=True
                )
            )

        if "ds_lines_total" in equipment:
            validated["equipment"]["ds_lines_total"] = int(
                validate_positive_number(
                    equipment["ds_lines_total"], "ds_lines_total", allow_zero=True
                )
            )

    # Validate volumes
    if "volumes" in data and isinstance(data["volumes"], dict):
        validated["volumes"] = {}
        volumes = data["volumes"]

        if "base_fermenter_vol_l" in volumes:
            validated["volumes"]["base_fermenter_vol_l"] = validate_positive_number(
                volumes["base_fermenter_vol_l"], "base_fermenter_vol_l"
            )

        if "working_volume_fraction" in volumes:
            validated["volumes"]["working_volume_fraction"] = validate_percentage(
                volumes["working_volume_fraction"], "working_volume_fraction"
            )

    # Pass through other fields for Pydantic validation
    for key in ["strains", "prices", "assumptions", "labor", "capex", "opex"]:
        if key in data:
            validated[key] = data[key]

    return validated


def validate_config_name(name: str) -> str:
    """
    Validate a configuration name for saving/loading.

    Args:
        name: Configuration name

    Returns:
        Validated name

    Raises:
        ValueError: If validation fails
    """
    if not name:
        raise ValueError("Configuration name cannot be empty")

    name = sanitize_string(name, MAX_CONFIG_NAME_LENGTH)

    # Check for path traversal attempts
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError("Configuration name contains invalid characters")

    return name


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.split("/")[-1].split("\\")[-1]

    # Remove null bytes and control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)

    # Only allow safe characters
    filename = re.sub(r'[^\w\-\.]', '_', filename)

    return filename


def validate_job_id(job_id: str) -> str:
    """
    Validate a job ID format.

    Args:
        job_id: Job ID to validate

    Returns:
        Validated job ID

    Raises:
        ValueError: If validation fails
    """
    if not job_id:
        raise ValueError("Job ID cannot be empty")

    # UUID format validation (basic)
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    if not uuid_pattern.match(job_id):
        # Allow simple alphanumeric IDs too (for testing)
        if not re.match(r'^[a-zA-Z0-9_\-]+$', job_id):
            raise ValueError("Invalid job ID format")

    return job_id


class InputValidator:
    """
    Main input validation class for API requests.
    """

    @staticmethod
    def validate_scenario(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate scenario input."""
        return validate_scenario_input(data)

    @staticmethod
    def validate_config_name(name: str) -> str:
        """Validate configuration name."""
        return validate_config_name(name)

    @staticmethod
    def validate_job_id(job_id: str) -> str:
        """Validate job ID."""
        return validate_job_id(job_id)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename."""
        return sanitize_filename(filename)
