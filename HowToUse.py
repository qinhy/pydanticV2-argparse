from typing import Optional, List, Union
from pydantic import BaseModel, Field
import pydanticV2_argparse
from pydanticV2_argparse.utils.types import is_field_a
import argparse
import ast
import collections.abc
import enum
import sys
from types import NoneType

class TestEnum(enum.Enum):
    """Test Enum for Testing."""

    A = enum.auto()
    B = enum.auto()
    C = enum.auto()

class Arguments(BaseModel):
    # Required Args
    string: str = Field(description="a required string")
    integer: int = Field(description="a required integer")
    flag: bool = Field(description="a required flag")    
    li: Union[List[str],None] = Field(None, description="str list") # "--li a b c"
    en: Optional[TestEnum] = None

    # Optional Args
    second_flag: bool = Field(False, description="an optional flag")
    third_flag: bool = Field(True, description="an optional flag")


def main() -> None:
    # Create Parser and Parse Args
    parser = pydanticV2_argparse.ArgumentParser(
        model=Arguments,
        prog="Example Program",
        description="Example Description",
        version="0.0.1",
        epilog="Example Epilog",
    )
    args = parser.parse_typed_args()

    # Print Args
    print(args.model_dump())
    return parser


if __name__ == "__main__":
    parser = main()
    
    # HowToUse.py --string 123 --integer 123 --flag
    # {'string': '123', 'integer': 123, 'flag': True, 'li': None, 'second_flag': False, 'third_flag': True}