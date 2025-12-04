"""Utility helpers for declarative typed argument parsing.

This module bundles helpers for formatting argument names and descriptions,
formatting validation errors, converting namespaces to dictionaries, building
dynamic pydantic validators, and inspecting field types.
"""

# Standard
import argparse
import sys
import types as _types
from typing import Any, Callable, Dict, Iterator, Literal, Optional, Tuple, Type, TypeVar, Union

# Third-Party
import pydantic as _pydantic
from pydantic_settings import SettingsError

# Version-Guarded
if sys.version_info < (3, 8):  # pragma: <3.8 cover
    from typing_extensions import get_args, get_origin
else:  # pragma: >=3.8 cover
    from typing import get_args, get_origin


# ---------------------------------------------------------------------------
# Shared Types
# ---------------------------------------------------------------------------

T = TypeVar("T")
PydanticModelT = TypeVar("PydanticModelT", bound=_pydantic.BaseModel)
PydanticValidator = Callable[..., Any]
PydanticError = Union[_pydantic.ValidationError, SettingsError]


# ---------------------------------------------------------------------------
# Argument formatting helpers
# ---------------------------------------------------------------------------

def name(field: _pydantic.fields.FieldInfo, invert: bool = False) -> str:
    """Standardise an argument name."""
    prefix = "--no-" if invert else "--"
    alias = field.alias or ""
    return f"{prefix}{alias.replace('_', '-')}"


def description(field: _pydantic.fields.FieldInfo) -> str:
    """Standardise an argument description."""
    default = f"(default: {field.get_default()})" if not field.is_required() else None
    return " ".join(filter(None, [field.description, default]))


# ---------------------------------------------------------------------------
# Error formatting helpers
# ---------------------------------------------------------------------------

def format_error(error: PydanticError) -> str:
    """Format a pydantic validation error for display."""
    return str(error)


# Backwards compatibility with the previous `errors.format` name
format = format_error  # noqa: A001


# ---------------------------------------------------------------------------
# Namespace helpers
# ---------------------------------------------------------------------------

def to_dict(namespace: argparse.Namespace) -> Dict[str, Any]:
    """Convert a possibly nested argparse namespace to a dictionary."""
    dictionary = vars(namespace)
    for (key, value) in dictionary.items():
        if isinstance(value, argparse.Namespace):
            dictionary[key] = to_dict(value)
    return dictionary


# ---------------------------------------------------------------------------
# Pydantic helpers
# ---------------------------------------------------------------------------

def as_validator(
    field_name: str,
    caster: Callable[[str], Any],
) -> PydanticValidator:
    """Wrap a caster and construct a validator for a given field."""

    @_pydantic.field_validator(field_name, mode="before")
    def __validator(cls: Type[Any], value: T) -> Union[T, None, Any]:
        if not isinstance(value, str):
            return value
        if not value:
            return None
        try:
            return caster(value)
        except Exception:
            return value

    __validator.__name__ = f"__pydanticV2_argparse_{field_name}"
    return __validator


def update_validators(
    validators: Dict[str, PydanticValidator],
    validator: Optional[PydanticValidator],
) -> None:
    """Update a validators dictionary in-place with a possible new validator."""
    if validator:
        validators[validator.__name__] = validator


def model_with_validators(
    model: Type[PydanticModelT],
    validators: Dict[str, PydanticValidator],
) -> Type[PydanticModelT]:
    """Generate a new pydantic model class with supplied validators."""
    model = _pydantic.create_model(
        model.__name__,
        __base__=model,
        __validators__=validators,
    )
    return model


# ---------------------------------------------------------------------------
# Type inspection helpers
# ---------------------------------------------------------------------------

def _iter_candidate_annotations(tp: Any) -> Iterator[Any]:
    """Yield non-None annotations from a (possibly union) annotation."""
    if tp is None:
        return

    origin = get_origin(tp)

    if origin is Union or origin is _types.UnionType:
        for arg in get_args(tp):
            if arg is type(None):
                continue
            yield from _iter_candidate_annotations(arg)
    else:
        yield tp


def _single_annotation_matches(annotation: Any, expected: Any) -> bool:
    """Check if a single annotation matches the expected type."""
    origin = get_origin(annotation)

    if origin is Literal:
        return expected is Literal or expected == Literal

    base = origin or annotation

    if base is expected or annotation is expected:
        return True

    if isinstance(base, type) and isinstance(expected, type):
        try:
            if issubclass(base, expected):
                return True
        except TypeError:
            pass

    if base == expected or annotation == expected:
        return True

    return False


def is_field_a(
    field: "_pydantic.fields.FieldInfo",
    types: Union[Any, Tuple[Any, ...]],
) -> bool:
    """Check whether the field's type matches any of the supplied types."""
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


# ---------------------------------------------------------------------------
# Compatibility namespaces
# ---------------------------------------------------------------------------

arguments = _types.SimpleNamespace(name=name, description=description)
errors = _types.SimpleNamespace(format=format_error)
namespaces = _types.SimpleNamespace(to_dict=to_dict)
pydantic = _types.SimpleNamespace(
    as_validator=as_validator,
    update_validators=update_validators,
    model_with_validators=model_with_validators,
    PydanticValidator=PydanticValidator,
)
types = _types.SimpleNamespace(
    is_field_a=is_field_a,
    _iter_candidate_annotations=_iter_candidate_annotations,
)


__all__ = (
    "PydanticError",
    "PydanticModelT",
    "PydanticValidator",
    "arguments",
    "as_validator",
    "description",
    "errors",
    "format",
    "format_error",
    "is_field_a",
    "model_with_validators",
    "name",
    "namespaces",
    "pydantic",
    "to_dict",
    "types",
)
