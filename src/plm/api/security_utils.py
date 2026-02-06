"""
Security Utilities

Common security functions for file uploads, input sanitization, and validation.
"""

import os
import re
import unicodedata
from typing import Optional

# Maximum file sizes by category (in bytes)
MAX_FILE_SIZES = {
    "document": 50 * 1024 * 1024,      # 50 MB
    "cad_model": 200 * 1024 * 1024,    # 200 MB for 3D models
    "cad_drawing": 100 * 1024 * 1024,  # 100 MB for drawings
    "image": 10 * 1024 * 1024,         # 10 MB
    "default": 25 * 1024 * 1024,       # 25 MB default
}

# Allowed filename characters pattern
SAFE_FILENAME_PATTERN = re.compile(r"[^\w\s\-\.\(\)]", re.UNICODE)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.

    Security measures:
    1. Strip directory components (prevent path traversal)
    2. Normalize unicode characters
    3. Remove or replace dangerous characters
    4. Limit filename length
    5. Handle empty/whitespace-only names

    Args:
        filename: The original filename from user input
        max_length: Maximum allowed filename length

    Returns:
        Sanitized filename safe for filesystem operations
    """
    if not filename:
        return "unnamed_file"

    # Normalize unicode to composed form
    filename = unicodedata.normalize("NFC", filename)

    # Strip directory components (key path traversal prevention)
    filename = os.path.basename(filename)

    # Remove null bytes and control characters
    filename = filename.replace("\x00", "").strip()

    # Remove dangerous path traversal patterns
    filename = filename.replace("..", "").replace("./", "").replace("/", "").replace("\\", "")

    # Split extension and name
    name, ext = os.path.splitext(filename)

    # Replace unsafe characters in name (keep extension chars for validation)
    name = SAFE_FILENAME_PATTERN.sub("_", name)

    # Collapse multiple underscores/spaces
    name = re.sub(r"[_\s]+", "_", name).strip("_")

    # Handle empty name after sanitization
    if not name:
        name = "file"

    # Truncate if needed (accounting for extension)
    if len(name) + len(ext) > max_length:
        name = name[:max_length - len(ext)]

    return name + ext


def validate_file_size(
    content_length: int,
    category: str = "default",
    custom_limit: Optional[int] = None,
) -> tuple[bool, str]:
    """
    Validate file size against limits.

    Args:
        content_length: Size of file in bytes
        category: Category key for MAX_FILE_SIZES lookup
        custom_limit: Override the default limit for this category

    Returns:
        Tuple of (is_valid, error_message)
    """
    max_size = custom_limit or MAX_FILE_SIZES.get(category, MAX_FILE_SIZES["default"])

    if content_length <= 0:
        return False, "File is empty"

    if content_length > max_size:
        max_mb = max_size / (1024 * 1024)
        actual_mb = content_length / (1024 * 1024)
        return False, f"File size ({actual_mb:.1f} MB) exceeds limit ({max_mb:.1f} MB)"

    return True, ""


def get_file_size_limit(category: str) -> int:
    """Get the file size limit for a category in bytes."""
    return MAX_FILE_SIZES.get(category, MAX_FILE_SIZES["default"])
