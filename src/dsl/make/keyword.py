from abc import ABC, abstractmethod
from typing import List, cast

from dsl.content import FixedTextNode
from dsl.make.var import MExpr, MVar


class MKeyword(FixedTextNode):
    """
    Simple fixed keyword node.
    The text passed here is the full line content.
    """

    def __init__(self, text: str) -> None:
        # Extract the keyword from the first token of the text
        parts = text.split(" ", maxsplit=1)
        self._name = parts[0] if parts else ""
        super().__init__(text, level=0)

    @property
    def name(self) -> str:
        """
        Keyword name, usually the first token of the line
        (for example "ifdef", "ifeq", "include", "define", "else").
        """
        return self._name

class MArgsKeyword(MKeyword, ABC):
    """
    Base keyword that takes arguments.
    Subclasses define how arguments are formatted in format_args.
    """

    def __init__(self, keyword: str, *args: MExpr) -> None:
        self._args: List[MExpr] = list(args)

        if args:
            full_text = keyword + " " + self.format_args(*args)
        else:
            full_text = keyword

        super().__init__(full_text)

    @staticmethod
    @abstractmethod
    def format_args(*args: MExpr) -> str:
        """
        Convert arguments to their string representation on the Makefile line.
        """
        raise NotImplementedError

    @property
    def args(self) -> List[MExpr]:
        return self._args


class MDefineKeyword(MArgsKeyword):
    """
    "define VAR" keyword. Accepts exactly one MVar argument.
    """

    def __init__(self, var: MVar) -> None:
        super().__init__("define", var)

    @staticmethod
    def format_args(*args: MExpr) -> str:
        if len(args) != 1:
            raise ValueError("define accepts exactly one argument")
        val = args[0]
        if not isinstance(val, MVar):
            raise TypeError("Expecting MVar for define argument")
        return cast(MVar, val).name


class MIncludeKeyword(MArgsKeyword):
    """
    Makefile include line.

    - Escapes spaces in each path ("foo bar" becomes "foo\\ bar")
    - Supports multiple paths, for example:
      MIncludeKeyword("a.mk", "b mk") -> "include a.mk b\\ mk"
    """

    def __init__(self, *args: MExpr) -> None:
        super().__init__("include", *args)

    @staticmethod
    def format_args(*args: MExpr) -> str:
        return " ".join(str(arg).replace(" ", r"\ ") for arg in args)


class MConditionKeyword(MArgsKeyword):
    """
    Base class for conditional directives: if, ifdef, ifndef, ifeq, ifneq, else, and else-prefixed variants.
    """

    def __init__(self, keyword: str, *args: MExpr) -> None:
        if not keyword:
            raise ValueError("Empty condition keyword is not allowed")
        super().__init__(keyword, *args)

    @staticmethod
    def format_args(*args: MExpr) -> str:
        """
        Default formatting rules:

        - 0 args: "" (used for "else")
        - 1 arg: variable name if MVar, otherwise str(expr)
        - 2 args: "(a,b)" with both converted to string
        """
        if not args:
            return ""

        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, MVar):
                return arg.name
            return str(arg)

        if len(args) == 2:
            left, right = args
            return "(" + ",".join(str(x) for x in (left, right)) + ")"

        raise ValueError("Condition keywords accept at most two arguments")

    def with_else_prefix(self) -> "MConditionKeyword":
        """
        Return a new condition keyword representing the "else" form
        of this condition.

        Examples:
        - ifdef VAR -> else ifdef VAR
        - ifeq (a,b) -> else ifeq (a,b)
        - else -> else
        """
        # Use the first token as the directive name, this matches Makefile syntax
        name = self.name

        # If the directive is already "else", we keep it as is
        if name == "else":
            new_keyword = "else"
        else:
            new_keyword = "else " + name

        return MConditionKeyword(new_keyword, *self.args)
