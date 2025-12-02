"""Parses Literal Pydantic Fields to Command-Line Arguments.

The `literal` module contains the `should_parse` function, which checks whether
this module should be used to parse the field, as well as the `parse_field`
function, which parses literal `pydantic` model fields to `ArgumentParser`
command-line arguments.
"""


# Standard
import argparse
import sys
from types import NoneType

# Third-Party
import pydantic

# Local
from .. import utils

# Typing
from typing import Any, Optional, Union, get_origin

# Version-Guarded
if sys.version_info < (3, 8):  # pragma: <3.8 cover
    from typing_extensions import Literal, get_args
else:  # pragma: >=3.8 cover
    from typing import Literal, get_args

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
    """Checks whether the field should be parsed as a `literal`.

    Args:
        field (pydantic.fields.FieldInfo): Field to check.

    Returns:
        bool: Whether the field should be parsed as a `literal`.
    """
    # Check and Return
    return utils.types.is_field_a(field, Literal)


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
    # Extract Choices
    choices = get_args(field.annotation)

    # Compute Argument Intrinsics
    is_flag = len(choices) == 1 and not bool(field.is_required())
    is_inverted = is_flag and field.get_default() is not None and allows_none(field)

    # Determine Argument Properties
    metavar = f"{{{', '.join(str(c) for c in choices)}}}"
    action = argparse._StoreConstAction if is_flag else argparse._StoreAction
    const = (
        {} if not is_flag else {"const": None} if is_inverted else {"const": choices[0]}
    )

    # Add Literal Field
    name = utils.arguments.name(field, is_inverted)
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

    # Construct String Representation Mapping of Choices
    # This allows us O(1) parsing of choices from strings
    mapping = {str(choice): choice for choice in choices}

    # Construct and Return Validator
    return utils.pydantic.as_validator(field, lambda v: mapping[v])
