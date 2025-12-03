from typing import Optional, List, Union
from pydantic import BaseModel, Field
import pydanticV2_argparse
import enum

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
    arg_62: List[str] = Field(
        default_factory=lambda: ["A", "B", "C"],
        description="arg_24",
    )
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
    return args


if __name__ == "__main__":
    args = main()