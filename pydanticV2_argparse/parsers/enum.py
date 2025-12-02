"""Parses Enum Pydantic Fields to Command-Line Arguments.

The `enum` module contains the `should_parse` function, which checks whether
this module should be used to parse the field, as well as the `parse_field`
function, which parses enum `pydantic` model fields to `ArgumentParser`
command-line arguments.
"""


# Standard
import argparse
import enum
from types import NoneType

# Third-Party
import pydantic

# Local
from .. import utils

# Typing
from typing import Any, Optional, Type, Union, get_args, get_origin


def allows_none(field: Any) -> bool:
    """Determine if a field allows None."""
    ann = getattr(field, "annotation", None)
    if ann is None: return False
    # Unwrap Annotated[...] if you use it
    origin = get_origin(ann)
    if origin is Union:
        return any(arg is NoneType for arg in get_args(ann))
    return ann is NoneType


def should_parse(field: pydantic.fields.FieldInfo) -> bool:
    """Checks whether the field should be parsed as an `enum`.

    Args:
        field (pydantic.fields.FieldInfo): Field to check.

    Returns:
        bool: Whether the field should be parsed as an `enum`.
    """
    # Check and Return
    return utils.types.is_field_a(field, enum.Enum)


def parse_field(
    parser: argparse.ArgumentParser,
    field: pydantic.fields.FieldInfo,
) -> Optional[utils.pydantic.PydanticValidator]:
    """Adds enum pydantic field to argument parser.

    Args:
        parser (argparse.ArgumentParser): Argument parser to add to.
        field (pydantic.fields.FieldInfo): Field to be added to parser.

    Returns:
        Optional[utils.pydantic.PydanticValidator]: Possible validator method.
    """
    # Extract Enum
    enum_type: Type[enum.Enum] = field.annotation

    # Compute Argument Intrinsics
    is_flag = len(enum_type) == 1 and not bool(field.is_required())
    is_inverted = is_flag and field.get_default() is not None and allows_none(field)

    # Determine Argument Properties
    metavar = f"{{{', '.join(e.name for e in enum_type)}}}"
    action = argparse._StoreConstAction if is_flag else argparse._StoreAction
    const = (
        {}
        if not is_flag
        else {"const": None}
        if is_inverted else {"const": list(enum_type)[0]}  # type: ignore[dict-item]
    )

    # Add Enum Field
    name = utils.arguments.name(field)
    alias = field.alias or name
    parser.add_argument(
        name,
        action=action,
        help=utils.arguments.description(field),
        dest=alias,
        metavar=metavar,
        required=bool(field.is_required()),
        **const,  # type: ignore[arg-type]
    )

    # Construct and Return Validator
    return utils.pydantic.as_validator(field, lambda v: enum_type[v])
