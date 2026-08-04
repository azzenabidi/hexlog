"""Input validation for user-editable fields.

Rules live here as pure functions so they are unit-testable without a GUI and
shared by every entity tab.
"""

import string

# Names may use letters, digits, spaces, and light punctuation; anything else
# (symbols, emoji, control characters) is treated as invalid input.
ALLOWED_NAME_CHARS = frozenset(string.ascii_letters + string.digits + " -_'.,()&")


def validate_name(name):
    """Return an error message for `name`, or None if it is acceptable.

    A name must not be blank and may only contain letters, digits, spaces,
    and basic punctuation (hyphens, apostrophes, and the like).
    """
    stripped = name.strip()
    if not stripped:
        return "Name cannot be empty."
    invalid = sorted({ch for ch in stripped if ch not in ALLOWED_NAME_CHARS})
    if invalid:
        return "Name cannot contain: " + " ".join(invalid)
    return None
