#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import List, Literal, Optional, Union

from dsl import Node,Stack,SimpleStack,BlankLine,Text,Block
from .var import MExpr

MElement = Node

class Makefile(Stack[MElement]):
    MARGIN:Optional[Node]=BlankLine()

    def __init__(self,*elements:MElement):
        super().__init__(*elements,inner=Makefile.MARGIN,outer=None)

class MList(SimpleStack[MElement]):
    pass

# ===== Comments and banners =====

class Comment(Text):
    def __init__(self, text: str):
        super().__init__(f"# {text}" if text else "#")

# ===== Assignments (LHS is a var) =====



# ===== Commands =====

class Command(Text):
    """
    Make recipe command line.

    __init__: takes a full command string (already built).
    """

    def __init__(self, line: str, *, silent: bool = False):
        if not isinstance(line, str):
            raise TypeError("Command line must be a str")
        text = line.lstrip()
        if silent and not text.startswith("@"):
            text = "@" + text
        super().__init__(text)


class ShellCommand(Command):
    """
    Convenience wrapper to build a command line from arguments.

        ShellCommand("echo", "hello", "$(VAR)")
        ShellCommand(M.var("CC"), M.var("CFLAGS"), "-o", "app", "main.o")

    str args are shell-escaped only when needed.
    MExpr args are inserted as-is.
    """

    # Safe tokens: letters, digits, '_', '-', '.', '/', ':'
    # Everything else (space, $, *, ?, quotes, etc.) triggers quoting.
    _SAFE_RE = re.compile(r"[A-Za-z0-9_\-./:]+$")

    @classmethod
    def _needs_quoting(cls, token: str) -> bool:
        if token == "":
            return True
        return cls._SAFE_RE.fullmatch(token) is None

    @staticmethod
    def _escape_token(token: str) -> str:
        """
        Shell-escape a string using single quotes, handling embedded
        single quotes in the standard POSIX way:
            foo'bar -> 'foo'"'"'bar'
        """
        if token == "":
            return "''"
        parts = token.split("'")
        return "'" + "'\"'\"'".join(parts) + "'"

    @classmethod
    def _format_arg(cls, arg: Union[str, MExpr]) -> str:
        if isinstance(arg, MExpr):
            # Insert make expression as-is, e.g. $(CC) or $(CFLAGS)
            return str(arg)
        if isinstance(arg, str):
            return cls._escape_token(arg) if cls._needs_quoting(arg) else arg
        raise TypeError("shell args must be str or MExpr")

    def __init__(self, *args: Union[str, MExpr], silent: bool = False):
        if not args:
            raise ValueError("ShellCommand requires at least one argument")
        parts: List[str] = [self._format_arg(a) for a in args]
        line = " ".join(parts)
        super().__init__(line, silent=silent)

# ===== Rules =====

class Rule(Block[Command]):
    """
    Builds exactly:

      <targets> <op> <prereqs> [| <order_only>]
        \t<recipe...>

    All inputs are used as-is. No normalization or splitting.
    """

    Op = Literal[":", "::", "&:"]

    def __init__(
        self,
        targets: Union[str, MExpr],
        prereqs: Optional[Union[str, MExpr]] = None,
        order_only: Optional[Union[str, MExpr]] = None,
        op: Op = ":",
    ):
        if op not in (":", "::", "&:"):
            raise ValueError(f"Invalid rule operator: {op}")

        left = str(targets).strip()
        if not left:
            raise ValueError("Rule requires a non-empty targets string or MExpr")

        right = "" if prereqs is None else str(prereqs).strip()
        oo = "" if order_only is None else str(order_only).strip()

        header = f"{left} {op}"
        if right:
            header += f" {right}"
        if oo:
            header += f" | {oo}"

        super().__init__(
            begin=Text(header),
            end=None,
            inner=None,
            outer=None
        )

class Phony(Rule):
    """
    .PHONY declaration helper.

    Use as:
        Phony('clean test lint')
        Phony(MConst('clean test'))
    """

    def __init__(self, targets: Union[str, MExpr]):
        if not str(targets).strip():
            raise ValueError(".PHONY requires at least one target")
        super().__init__(".PHONY", targets, op=":")

class Line(Text):
    """
    Wrap a Make expression so it can live as a top level Makefile element.

    Example:
        mf.append(MExprLine(M.eval(M.Const("include other.mk"))))

    Renders as:
        $(eval include other.mk)
    """

    def __init__(self, expr: MExpr):
        if not isinstance(expr, MExpr):
            raise TypeError(f"MExprLine expects an MExpr, got {type(expr).__name__}")
        super().__init__(str(expr))
