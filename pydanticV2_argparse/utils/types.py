"""Types Utility Functions for Declarative Typed Argument Parsing.

The `types` module contains utility helpers used for determining and comparing
the types of `pydantic` fields across both Pydantic v1 and v2.
"""


# Standard
import sys
from types import NoneType, SimpleNamespace

# Third-Party
import pydantic

# Typing
from typing import Any, Dict, Tuple, Union

# Version-Guarded
if sys.version_info < (3, 8):  # pragma: <3.8 cover
    from typing_extensions import get_args, get_origin
else:  # pragma: >=3.8 cover
    from typing import get_args, get_origin


# Undefined sentinels used by different pydantic versions
try:  # pragma: no cover - import guard
    from pydantic_core import PydanticUndefined  # type: ignore
except Exception:  # pragma: no cover - fallback when pydantic-core isn't present
    PydanticUndefined = object()

Undefined = getattr(pydantic.fields, "Undefined", object())


def get_field_type(field: Any) -> Any:
    """Return the annotated/outer type for a field in a compatible way."""
    for attr in ("outer_type_", "annotation", "type_"):
        if hasattr(field, attr):
            value = getattr(field, attr)
            if value is not None:
                return value
    raise ValueError(f"can not get field type of {field}")


def is_field_a(
    field: pydantic.fields.FieldInfo,
    types: Union[Any, Tuple[Any, ...]],
) -> bool:
    """Checks whether the subject *is* any of the supplied types.

    The checks are performed as follows:

    1. `field` *is* one of the `types`
    2. `field` *is an instance* of one of the `types`
    3. `field` *is a subclass* of one of the `types`

    If any of these conditions are `True`, then the function returns `True`,
    else `False`.

    Args:
        field (pydantic.fields.FieldInfo): Subject field to check type of.
        types (Union[Any, Tuple[Any, ...]]): Type(s) to compare field against.

    Returns:
        bool: Whether the field *is* considered one of the types.
    """
    # Create tuple if only one type was provided
    if not isinstance(types, tuple):
        types = (types,)

    # Get field type, or origin if applicable
    field_type = get_origin(get_field_type(field)) or get_field_type(field)
    if field_type is None:
        return False

    # Check `isinstance` and `issubclass` validity
    # In order for `isinstance` and `issubclass` to be valid, all arguments
    # should be instances of `type`, otherwise `TypeError` *may* be raised.
    is_valid = all(isinstance(t, type) for t in (*types, field_type))

    # Perform checks and return
    return (
        field_type in types
        or (is_valid and isinstance(field_type, types))
        or (is_valid and issubclass(field_type, types))
    )


def get_model_fields(model: Any) -> Dict[str, Any]:
    """Retrieve a model's fields mapping with Pydantic v1/v2 compatibility."""
    if hasattr(model, "model_fields"):
        return getattr(model, "model_fields")
    if hasattr(model, "model_fields"):
        return getattr(model, "model_fields")
    return {}


def is_required(field: Any) -> bool:
    """Determine whether a field is required across pydantic versions."""
    if hasattr(field, "is_required"):
        return bool(field.is_required())
    if hasattr(field, "required"):
        return bool(getattr(field, "required"))
    default = getattr(field, "default", PydanticUndefined)
    if default not in (Undefined, PydanticUndefined):
        return False
    if getattr(field, "default_factory", None):
        return False
    return True


def get_default(field: Any) -> Any:
    """Retrieve a field's default value or None if it is undefined."""
    if hasattr(field, "get_default") and callable(field.get_default):
        try:
            return field.get_default()
        except TypeError:
            # Some implementations expect parameters; ignore and continue
            pass

    default_factory = getattr(field, "default_factory", None)
    if default_factory:
        try:
            return default_factory()
        except TypeError:
            return default_factory() if callable(default_factory) else default_factory

    default = getattr(field, "default", PydanticUndefined)
    if default in (Undefined, PydanticUndefined):
        return None
    return default


def field_alias(field: Any, fallback: str) -> str:
    """Return the field's alias, defaulting to the provided fallback."""
    alias = getattr(field, "alias", None)
    return alias or fallback


def field_description(field: Any) -> str:
    """Return a field's description string if present."""
    return getattr(field, "description", "") or ""


def allows_none(field: Any) -> bool:
    """Determine if a field allows None."""
    ann = getattr(field, "annotation", None)
    if ann is None: return False
    # Unwrap Annotated[...] if you use it
    origin = get_origin(ann)
    if origin is Union:
        return any(arg is NoneType for arg in get_args(ann))
    return ann is NoneType


def field_name(field: Any, fallback: str) -> str:
    """Return the field name for use with validators."""
    name = getattr(field, "name", None)
    return name or fallback


class FieldWrapper:
    def __init__(self, name: str, field: pydantic.fields.FieldInfo) -> None:
        self._field = field
        self.name = name
        self.alias = field.alias or name
    def __getattr__(self, item: str) -> Any:
        return getattr(self._field, item)


def ensure_model_field(name: str, field: pydantic.fields.FieldInfo) -> Any:
    return FieldWrapper(name,field)
