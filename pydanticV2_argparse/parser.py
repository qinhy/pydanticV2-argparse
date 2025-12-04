"""Declarative and Typed Argument Parser.

The `parser` module contains the `ArgumentParser` class, which provides a
declarative method of defining command-line interfaces.

The procedure to declaratively define a typed command-line interface is:

1. Define `pydantic` arguments model
2. Create typed `ArgumentParser`
3. Parse typed arguments

The resultant arguments object returned is an instance of the defined
`pydantic` model. This means that the arguments object and its attributes will
be compatible with an IDE, linter or type checker.
"""


# Standard
import argparse
import ast
import collections.abc
import enum
import sys
NoneType = type(None)

# Third-Party
import pydantic
from pydantic_settings import BaseSettings, SettingsError

# Local
from . import utils
from . import actions
from . import patches  # noqa: F401

# Typing
from typing import Any, Callable, Dict, Generic, List, Literal, NoReturn, Optional, Type, TypeVar, Union, cast, get_args, get_origin


# Constants
PydanticModelT = TypeVar("PydanticModelT", bound=pydantic.BaseModel)

def allows_none(field: Any) -> bool:
    """Determine if a field allows None."""
    ann = getattr(field, "annotation", None)
    if ann is None:
        return False
    # Unwrap Annotated[...] if you use it
    origin = get_origin(ann)
    if origin is Union:
        return any(arg is NoneType for arg in get_args(ann))
    return ann is NoneType

class ArgumentParser(argparse.ArgumentParser, Generic[PydanticModelT]):
    """Declarative and Typed Argument Parser.

    The `ArgumentParser` declaratively generates a command-line interface using
    the `pydantic` model specified upon instantiation.

    The `ArgumentParser` provides the following `argparse` functionality:

    * Required Arguments
    * Optional Arguments
    * Subcommands

    All arguments are *named*, and positional arguments are not supported.

    The `ArgumentParser` provides the method `parse_typed_args()` to parse
    command line arguments and return an instance of its bound `pydantic`
    model, populated with the parsed and validated user supplied command-line
    arguments.
    """

    # Argument Group Names
    COMMANDS = "commands"
    REQUIRED = "required arguments"
    OPTIONAL = "optional arguments"
    HELP = "help"

    # Keyword Arguments
    KWARG_REQUIRED = "required"

    # Exit Codes
    EXIT_ERROR = 2

    def __init__(
        self,
        model: Type[PydanticModelT],
        prog: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        epilog: Optional[str] = None,
        add_help: bool = True,
        exit_on_error: bool = True,
    ) -> None:
        """Instantiates the Typed Argument Parser with its `pydantic` model.

        Args:
            model (Type[PydanticModelT]): Pydantic argument model class.
            prog (Optional[str]): Program name for CLI.
            description (Optional[str]): Program description for CLI.
            version (Optional[str]): Program version string for CLI.
            epilog (Optional[str]): Optional text following help message.
            add_help (bool): Whether to add a `-h`/`--help` flag.
            exit_on_error (bool): Whether to exit on error.
        """
        # Initialise Super Class
        if sys.version_info < (3, 9):  # pragma: <3.9 cover
            super().__init__(
                prog=prog,
                description=description,
                epilog=epilog,
                add_help=False,  # Always disable the automatic help flag.
                argument_default=argparse.SUPPRESS,  # Allow `pydantic` to handle defaults.
            )

        else:  # pragma: >=3.9 cover
            super().__init__(
                prog=prog,
                description=description,
                epilog=epilog,
                exit_on_error=exit_on_error,
                add_help=False,  # Always disable the automatic help flag.
                argument_default=argparse.SUPPRESS,  # Allow `pydantic` to handle defaults.
            )

        # Set Version, Add Help and Exit on Error Flag
        self.version = version
        self.add_help = add_help
        self.exit_on_error = exit_on_error

        # Add Arguments Groups
        self._subcommands: Optional[argparse._SubParsersAction] = None
        self._required_group = self.add_argument_group(ArgumentParser.REQUIRED)
        self._optional_group = self.add_argument_group(ArgumentParser.OPTIONAL)
        self._help_group = self.add_argument_group(ArgumentParser.HELP)

        # Add Help and Version Flags
        if self.add_help:
            self._add_help_flag()
        if self.version:
            self._add_version_flag()

        # Add Arguments from Model
        self.model = self._add_model(model)

    def parse_typed_args(
        self,
        args: Optional[List[str]] = None,
        namespace: Optional[argparse.Namespace] = None,
    ) -> PydanticModelT:
        """Parses command line arguments.

        If `args` are not supplied by the user, then they are automatically
        retrieved from the `sys.argv` command-line arguments.

        Args:
            args (Optional[List[str]]): Optional list of arguments to parse.
            namespace (Optional[argparse.Namespace]): Existing namespace to populate.

        Returns:
            PydanticModelT: Populated instance of typed arguments model.

        Raises:
            argparse.ArgumentError: Raised upon error, if not exiting on error.
            SystemExit: Raised upon error, if exiting on error.
        """
        # First, let argparse parse CLI args. Right now there are no
        # user-defined arguments, so this effectively just handles -h/--help
        # and basic error reporting.
        # Call Super Class Method
        namespace = self.parse_args(args, namespace)

        # Convert Namespace to Dictionary
        arguments = utils.to_dict(namespace)

        # Handle Possible Validation Errors
        try:
            # Convert Namespace to Pydantic Model
            if issubclass(self.model, BaseSettings):
                arguments.update(_env_parse_none_str="")
            model = self.model(**arguments)

        except (pydantic.ValidationError, SettingsError) as exc:
            # Catch exceptions, and use the ArgumentParser.error() method
            # to report it to the user
            self.error(utils.format(exc))

        # Return
        return model

    def add_argument(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> argparse.Action:
        """Adds an argument to the ArgumentParser.

        Args:
            *args (Any): Positional args to be passed to super class method.
            **kwargs (Any): Keyword args to be passed to super class method.

        Returns:
            argparse.Action: Action generated by the argument.
        """
        # Check whether the argument is required or optional
        # We intercept the keyword arguments and "pop" here so that the
        # `required` kwarg can never be passed through to the parent
        # `ArgumentParser`, allowing Pydantic to perform all of the validation
        # and error handling itself.
        if kwargs.pop(ArgumentParser.KWARG_REQUIRED):
            # Required
            group = self._required_group

        else:
            # Optional
            group = self._optional_group

        # Return Action
        return group.add_argument(*args, **kwargs)

    def error(self, message: str) -> NoReturn:
        """Prints a usage message to `stderr` and exits if required.

        Args:
            message (str): Message to print to the user.

        Raises:
            argparse.ArgumentError: Raised if not exiting on error.
            SystemExit: Raised if exiting on error.
        """
        # Print usage message
        self.print_usage(sys.stderr)

        # Check whether parser should exit
        if self.exit_on_error:
            self.exit(ArgumentParser.EXIT_ERROR, f"{self.prog}: error: {message}\n")

        # Raise Error
        raise argparse.ArgumentError(None, f"{self.prog}: error: {message}")

    def _commands(self) -> argparse._SubParsersAction:
        """Creates and Retrieves Subcommands Action for the ArgumentParser.

        Returns:
            argparse._SubParsersAction: SubParsersAction for the subcommands.
        """
        # Check for Existing Sub-Commands Group
        if not self._subcommands:
            # Add Sub-Commands Group
            self._subcommands = self.add_subparsers(
                title=ArgumentParser.COMMANDS,
                action=actions.SubParsersAction,
                required=True,
            )

            # Shuffle Group to the Top for Help Message
            self._action_groups.insert(0, self._action_groups.pop())

        # Return
        return self._subcommands

    def _add_help_flag(self) -> None:
        """Adds help flag to argparser."""
        # Add help flag
        self._help_group.add_argument(
            "-h",
            "--help",
            action=argparse._HelpAction,
            help="show this help message and exit",
        )

    def _add_version_flag(self) -> None:
        """Adds version flag to argparser."""
        # Add version flag
        self._help_group.add_argument(
            "-v",
            "--version",
            action=argparse._VersionAction,
            help="show program's version number and exit",
        )

    def _add_model(self, model: Type[PydanticModelT]) -> Type[PydanticModelT]:
        """Adds the `pydantic` model to the argument parser.

        This method also generates "validators" for the arguments derived from
        the `pydantic` model, and generates a new subclass from the model
        containing these validators.

        Args:
            model (Type[PydanticModelT]): Pydantic model class to add to the
                argument parser.

        Returns:
            Type[PydanticModelT]: Pydantic model possibly with new validators.
        """
        # Initialise validators dictionary
        self.validators: Dict[str, utils.PydanticValidator] = {}

        # Loop through fields in model
        for name, model_field in model.model_fields.items():
            field: pydantic.fields.FieldInfo = model_field
            field.alias = field.alias or name
            # Add field
            validator = self._add_field(field, name)

            # Update validators
            utils.update_validators(self.validators, validator)

        # Construct and return model with validators
        return utils.model_with_validators(model, self.validators)

    def _add_field(
        self,
        field: pydantic.fields.FieldInfo,
        name: str,
    ) -> Optional[utils.PydanticValidator]:
        """Adds `pydantic` field to argument parser.

        Args:
            field (pydantic.fields.FieldInfo): Field to be added to parser.
            name (str): Name override for parser argument.

        Returns:
            Optional[utils.PydanticValidator]: Possible validator.
        """
        is_command = utils.is_field_a(field, pydantic.BaseModel)
        is_boolean = utils.is_field_a(field, bool)
        is_container = utils.is_field_a(field, collections.abc.Container) and not utils.is_field_a(
            field, (collections.abc.Mapping, enum.Enum, str, bytes)
        )
        is_mapping = utils.is_field_a(field, collections.abc.Mapping)
        is_literal = utils.is_field_a(field, Literal)
        is_enum = utils.is_field_a(field, enum.Enum)

        validator: Optional[utils.PydanticValidator] = utils.as_validator(name, lambda v: v)

        if is_command:
            alias = field.alias or name
            self._commands().add_parser(
                alias,
                help=field.description,
                model=next(utils._iter_candidate_annotations(field.annotation)),
                exit_on_error=False,
            )
            validator = None

        elif is_literal:
            literal_args = [choice for choice in get_args(field.annotation) if choice is not NoneType]
            choices: List[Any] = []
            for literal in literal_args:
                if get_origin(literal) == Literal:
                    choices.extend(get_args(literal))
                else:
                    choices.append(literal)

            is_flag = len(choices) == 1 and not field.is_required()
            is_inverted = is_flag and field.get_default() is not None and allows_none(field)
            metavar = f"{{{', '.join(str(choice) for choice in choices)}}}"
            literal_action: Type[argparse.Action] = argparse._StoreConstAction if is_flag else argparse._StoreAction
            literal_kwargs: Dict[str, Any] = {}
            if is_flag:
                const_value = None if is_inverted else choices[0]
                literal_kwargs = {"const": const_value}
                if allows_none(field):
                    inverted_kwargs: Dict[str, Any] = {"const": None}
                    self._add_argument_base(
                        name=name,
                        field=field,
                        action=literal_action,
                        metavar=metavar,
                        is_inverted=True,
                        **inverted_kwargs,
                    )

            self._add_argument_base(name=name, field=field, action=literal_action, metavar=metavar, **literal_kwargs)
            mapping = {str(choice): choice for choice in choices}
            validator = utils.as_validator(name, lambda v: mapping[str(v)])

        elif is_boolean:
            is_inverted = not field.is_required() and bool(field.get_default())
            action: Type[argparse.Action]
            if field.is_required():
                action = actions.BooleanOptionalAction
            elif is_inverted:
                action = argparse._StoreFalseAction
            else:
                action = argparse._StoreTrueAction
            self._add_argument_base(
                name=name,
                field=field,
                action=action,
                no_metavar=True,
                is_inverted=is_inverted,
            )

        elif is_container:
            self._add_argument_base(
                name=name,
                field=field,
                action=argparse._StoreAction,
                nargs=argparse.ONE_OR_MORE,
            )

        elif is_mapping:
            self._add_argument_base(
                name=name,
                field=field,
                action=argparse._StoreAction,
            )
            validator = utils.as_validator(name, lambda v: ast.literal_eval(v))

        elif is_enum:
            enum_type: Type[enum.Enum] = next(utils._iter_candidate_annotations(field.annotation))
            is_flag = len(enum_type) == 1 and not field.is_required()
            metavar = f"{{{', '.join(e.name for e in enum_type)}}}"
            enum_action = argparse._StoreConstAction if is_flag else argparse._StoreAction
            enum_kwargs: Dict[str, Any] = {}
            if is_flag:
                enum_kwargs = {"const": next(iter(enum_type))}

                if allows_none(field):
                    inverted_enum_kwargs: Dict[str, Any] = {"const": None}
                    self._add_argument_base(
                        name=name,
                        field=field,
                        action=enum_action,
                        metavar=metavar,
                        is_inverted=True,
                        **inverted_enum_kwargs,
                    )

            self._add_argument_base(name=name, field=field, action=enum_action, metavar=metavar, **enum_kwargs)
            return utils.as_validator(name, lambda v: enum_type[v])

        else:
            self._add_argument_base(name=name, field=field, action=argparse._StoreAction)

        return validator

    def _add_argument_base(
        self,
        name: str,
        field: pydantic.fields.FieldInfo,
        action: Type[argparse.Action],
        default_str: Any = None,
        metavar: Optional[str] = None,
        no_metavar: bool = False,
        is_inverted: bool = False,
        **extra: Any,
    ) -> None:
        cli_name = utils.name(field, is_inverted)
        alias = field.alias or name
        if default_str is None:
            default_str = field.get_default()
            if field.default_factory:
                factory = cast(Callable[[], Any], field.default_factory)
                default_str = factory()
        # Construct Default String
        default_str = f"(default: {default_str})" if not field.is_required() else None
        # # Return Standardised Description String
        help_message = " ".join(filter(None, [field.description, default_str]))

        args = dict(
            action=action,
            help=help_message,
            dest=alias,
            metavar=(metavar or alias.upper()),
            required=field.is_required(),
            **extra,
        )
        if no_metavar:
            del args["metavar"]
        self.add_argument(cli_name, **args)
        return None
