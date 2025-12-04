"""Declarative Typed Argument Parsing with Pydantic Models.

This is the `pydanticV2-argparse` package, which contains the classes, methods
and functions required for declarative and typed argument parsing with
`pydantic` models.

The public interface exposed by this package is the declarative and typed
`ArgumentParser` class, as well as the package "dunder" metadata.
"""

# Local

# important! must do first
from . import patches

from .parser import ArgumentParser


# Public Re-Exports
__all__ = (
    "ArgumentParser",
)
