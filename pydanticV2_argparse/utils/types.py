"""Types Utility Functions for Declarative Typed Argument Parsing.

The `types` module contains utility helpers used for determining and comparing
the types of `pydantic` fields across both Pydantic v1 and v2.
"""


# Standard
import sys
from typing import Any, Tuple, Union, get_origin, get_args, Literal
import types as _types

# Third-Party
import pydantic

# Typing
from typing import Any, Tuple, Union

# Version-Guarded
if sys.version_info < (3, 8):  # pragma: <3.8 cover
    from typing_extensions import get_args, get_origin
else:  # pragma: >=3.8 cover
    from typing import get_args, get_origin

# def is_field_a(
#     field: pydantic.fields.FieldInfo,
#     types: Union[Any, Tuple[Any, ...]],
# ) -> bool:
#     """Checks whether the subject *is* any of the supplied types.

#     The checks are performed as follows:

#     1. `field` *is* one of the `types`
#     2. `field` *is an instance* of one of the `types`
#     3. `field` *is a subclass* of one of the `types`

#     If any of these conditions are `True`, then the function returns `True`,
#     else `False`.

#     Args:
#         field (pydantic.fields.FieldInfo): Subject field to check type of.
#         types (Union[Any, Tuple[Any, ...]]): Type(s) to compare field against.

#     Returns:
#         bool: Whether the field *is* considered one of the types.
#     """
#     # Create tuple if only one type was provided
#     if not isinstance(types, tuple):
#         types = (types,)

#     # Get field type, or origin if applicable
#     field_type = get_origin(field.annotation) or field.annotation
#     if field_type is None:
#         return False

#     # Check `isinstance` and `issubclass` validity
#     # In order for `isinstance` and `issubclass` to be valid, all arguments
#     # should be instances of `type`, otherwise `TypeError` *may* be raised.
#     is_valid = all(isinstance(t, type) for t in (*types, field_type))

#     # Perform checks and return
#     return (
#         field_type in types
#         or (is_valid and isinstance(field_type, types))
#         or (is_valid and issubclass(field_type, types))
#     )

def _iter_candidate_annotations(tp: Any):
    """Yield non-None annotations from a (possibly union) annotation.

    Examples:
        Optional[List[str]] -> yields `typing.List[str]`
        List[str] | None    -> yields `list[str]`
        List[str]           -> yields `list[str]`
        bool                -> yields `bool`
    """
    if tp is None:
        return

    origin = get_origin(tp)

    # Handle Union / | syntax / Optional[T]
    if origin is Union or origin is _types.UnionType:
        for arg in get_args(tp):
            if arg is type(None):
                # Skip the None part of Optional[T]
                continue
            # Recurse in case of nested Unions
            yield from _iter_candidate_annotations(arg)
    else:
        yield tp


def _single_annotation_matches(annotation: Any, expected: Any) -> bool:
    """Does a single (non-union) annotation match `expected`?"""
    origin = get_origin(annotation)

    # --- Special case: Literal[...] ---
    # Your tests expect:
    #   Literal["A"]     -> matches Literal
    #   Literal[1,2,3]   -> matches Literal
    if origin is Literal:
        return expected is Literal or expected == Literal

    # For "normal" generics, use their origin:
    #   List[str]  -> list
    #   Dict[...]  -> dict
    #   Deque[...] -> collections.deque
    base = origin or annotation

    # 1. Exact identity (covers simple cases & subclasses directly)
    if base is expected or annotation is expected:
        return True

    # 2. issubclass for real classes / ABCs (e.g. list -> Container, dict -> Mapping)
    if isinstance(base, type) and isinstance(expected, type):
        try:
            if issubclass(base, expected):
                return True
        except TypeError:
            # Defensive: some weird typing objects may still slip through
            pass

    # 3. Fallback equality (for some typing constructs with value equality)
    if base == expected or annotation == expected:
        return True

    return False


def is_field_a(
    field: "pydantic.fields.FieldInfo",
    types: Union[Any, Tuple[Any, ...]],
) -> bool:
    """Checks whether the field's *type* matches any of the supplied types.

    Supports:
      - bare types: bool, int, str, bytes, ...
      - typing generics: List, List[str], Dict, Dict[str, int], Deque[str], ...
      - ABCs: collections.abc.Container, collections.abc.Mapping, ...
      - Optional / Union: Optional[List[str]], List[str] | None, ...
      - Literal: Literal["A"], Literal[1, 2, 3] vs Literal
      - Class hierarchies: subclasses of BaseModel, Enum, etc.
    """
    # Normalise `types` to a tuple
    if not isinstance(types, tuple):
        types = (types,)

    field_type = field.annotation
    if field_type is None:
        return False

    candidates = list(_iter_candidate_annotations(field_type))
    if not candidates:
        return False

    for ann in candidates:
        for expected in types:
            if _single_annotation_matches(ann, expected):
                return True

    return False




















