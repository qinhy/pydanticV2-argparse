"""Regression tests for conventional required CLI argument reporting."""

from __future__ import annotations

import argparse
from typing import List

import pydantic
import pytest
from pydantic_settings import BaseSettings

from pydanticV2_argparse import ArgumentParser


class RequiredArguments(pydantic.BaseModel):
    """Model with required values and an optional flag."""

    string: str
    integer: int
    flag: bool
    second_flag: bool = False


@pytest.mark.parametrize("exit_on_error", [True, False])
@pytest.mark.parametrize(
    ("arguments", "missing"),
    [
        ([], "--string, --integer, --flag/--no-flag"),
        (["--string", "hello", "--integer", "42"], "--flag/--no-flag"),
    ],
)
def test_missing_required_arguments(
    arguments: List[str], missing: str, exit_on_error: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    """Report missing CLI options without Pydantic's validation dump."""
    parser = ArgumentParser(RequiredArguments, prog="example", exit_on_error=exit_on_error)
    error = SystemExit if exit_on_error else argparse.ArgumentError
    message = f"the following arguments are required: {missing}"

    with pytest.raises(error) as exc:
        parser.parse_typed_args(arguments)

    captured = capsys.readouterr()
    if exit_on_error:
        assert isinstance(exc.value, SystemExit)
        assert exc.value.code == 2
        assert f"example: error: {message}" in captured.err
    else:
        assert message in str(exc.value)
    assert "validation error" not in captured.err
    assert "errors.pydantic.dev" not in captured.err
    assert captured.out == ""


def test_required_arguments_usage() -> None:
    """Usage marks only optional values with brackets."""
    parser = ArgumentParser(RequiredArguments, prog="example")
    usage = parser.format_usage()
    # Python 3.8's formatter shows only the first spelling of boolean options.
    assert "--string STRING --integer INTEGER --flag" in " ".join(usage.split())
    assert "[--string" not in usage
    assert "[--integer" not in usage
    assert "[--flag" not in usage
    assert "[--second-flag]" in usage
    help_message = parser.format_help()
    assert "required arguments:" in help_message
    assert "--flag, --no-flag" in help_message


@pytest.mark.parametrize("flag", ["--flag", "--no-flag"])
def test_required_boolean_options(flag: str) -> None:
    """Either spelling satisfies a required boolean option."""
    parser = ArgumentParser(RequiredArguments)
    args = parser.parse_typed_args(["--string", "hello", "--integer", "42", flag])
    assert args.string == "hello"
    assert args.integer == 42
    assert args.flag is (flag == "--flag")
    assert args.second_flag is False


def test_required_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings can still satisfy required fields through the environment."""
    class Settings(BaseSettings):
        """Settings with a required environment value."""

        required_value: int

    monkeypatch.setenv("REQUIRED_VALUE", "42")
    parser = ArgumentParser(Settings)
    assert "[--required-value REQUIRED_VALUE]" in parser.format_usage()
    assert parser.parse_typed_args([]).required_value == 42
