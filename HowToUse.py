
from pydantic import BaseModel, Field
import pydanticV2_argparse


class Arguments(BaseModel):
    # Required Args
    string: str = Field(description="a required string")
    integer: int = Field(description="a required integer")
    flag: bool = Field(description="a required flag")

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
    print(args)


if __name__ == "__main__":
    main()