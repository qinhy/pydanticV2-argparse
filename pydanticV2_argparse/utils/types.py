"""Types Utility Functions for Declarative Typed Argument Parsing.

The `types` module contains utility helpers used for determining and comparing
the types of `pydantic` fields across both Pydantic v1 and v2.
"""


# Standard
import sys
from types import NoneType, SimpleNamespace
import types

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
    types_: Union[Any, Tuple[Any, ...]],
) -> bool:
    # Normalize types to a tuple
    if not isinstance(types_, tuple):
        types_ = (types_,)

    field_type = get_field_type(field)
    if field_type is None:
        return False

    origin = get_origin(field_type)

    # Handle Union / Optional specially
    if origin in (Union, types.UnionType):
        # Extract args, drop NoneType, unwrap any generics
        candidate_types = []
        for arg in get_args(field_type):
            if arg is type(None):
                continue  # skip Optional's None
            arg_origin = get_origin(arg)
            candidate_types.append(arg_origin or arg)
    else:
        # Non-union: unwrap generics once
        candidate_types = [origin or field_type]

    if not candidate_types:
        # e.g. field_type is just NoneType
        return False

    # Now run your checks against each concrete candidate type
    for ft in candidate_types:
        # 1. exact match
        if ft in types_:
            return True

        # 2. subclass / ABC check (Container, Sequence, etc.)
        if isinstance(ft, type):
            for t in types_:
                if isinstance(t, type):
                    try:
                        if issubclass(ft, t):
                            return True
                    except TypeError:
                        # typing artefacts that don't support issubclass
                        pass

    return False

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
