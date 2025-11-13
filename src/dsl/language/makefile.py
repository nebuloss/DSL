#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import List, Literal, Optional, Union

from dsl.core import language
from dsl.variable.makefile import MExpr, MVar, MConst

MElement = language.Node

class Makefile(language.Stack):
    def __init__(self):
        super().__init__(language.BlankLine(), True, False)

# ===== Comments and banners =====

class MComment(language.Text):
    def __init__(self, text: str):
        super().__init__(f"# {text}" if text else "#")


class MBanner(language.Node):
    def __init__(self, title: str, width: int = 60, char: str = "#"):
        self._title = title.strip()
        self._char = char[0] if char else "#"
        self._width = max(width, len(self._title) + 4)

    @property
    def lines(self) -> List[str]:
        bar = self._char * self._width
        if not self._title:
            return [bar]
        mid = f"{self._char} {self._title}"
        if len(mid) < self._width:
            mid += " " * (self._width - len(mid))
        return [bar, self._char, mid, self._char, bar]


MBlankLine=language.BlankLine

# ===== Assignments (LHS is a var) =====

class MAssignment(language.Text):
    """
    VAR op VALUE

    Operators:
      =    recursive
      :=   simple
      ?=   set if not set
      +=   append
    """

    def __init__(self, var: MVar, value: MExpr, op: str = "="):
        op = op.strip()
        if op not in ("=", ":=", "?=", "+="):
            raise ValueError(f"Invalid assignment operator: {op}")
        super().__init__(f"{var.name} {op} {value}")


class MSet(MAssignment):
    def __init__(self, var: MVar, value: MExpr):
        super().__init__(var, value, "=")


class MSetImmediate(MAssignment):
    def __init__(self, var: MVar, value: MExpr):
        super().__init__(var, value, ":=")


class MSetDefault(MAssignment):
    def __init__(self, var: MVar, value: MExpr):
        super().__init__(var, value, "?=")


class MAppend(MAssignment):
    def __init__(self, var: MVar, value: MExpr):
        super().__init__(var, value, "+=")


class MAssignments(language.WordAlignedStack[MAssignment]):
    def __init__(self):
        super().__init__(limit=2)

# ===== Conditionals (Makefile syntax) =====

class MIfExpr(language.Block[MElement]):
    """
    Block with else-if chaining and else body.

    begin:  "if ..."   | "ifdef ..." | "ifndef ..." | "ifeq (...)" | "ifneq (...)"
    end:    "endif"

    Else-if rendering rule:
      for block in Elif:
          cond_lines = block.lines
          if len(cond_lines) >= 2:
              emit "else " + cond_lines[0]
              emit cond_lines[1:-1]   # skip inner "endif"
    """

    def __init__(
        self,
        header: str,
        *body: MElement,
        margin: Optional[language.Node] = None,
        inner: bool = True,
        outer: bool = False,
    ):
        super().__init__(
            begin=language.Text(header.strip()),
            end=language.Text("endif"),
            margin=margin,
            inner=inner,
            outer=outer,
        )

        self._elif: language.Stack["MIfExpr"] = language.Stack(
            margin=margin,
            inner=inner,
            outer=outer,
        )
        self._else: language.Stack[MElement] = language.Stack(
            margin=margin,
            inner=inner,
            outer=outer,
        )

        self.extend(body)

    @property
    def Elif(self) -> language.Stack["MIfExpr"]:
        """Chained else-if blocks."""
        return self._elif

    @property
    def Else(self) -> language.Stack[MElement]:
        """Final else body."""
        return self._else

    @property
    def lines(self) -> List[str]:
        out: List[str] = super().lines
        if not out:
            return out

        # Remove our own "endif"
        endif_line = out.pop()

        # Else-if branches
        for block in self._elif:
            cond_lines = block.lines
            if len(cond_lines) >= 2:
                out.append("else " + cond_lines[0])
                out.extend(cond_lines[1:-1])

        # Final else
        else_lines = self._else.lines
        if else_lines:
            out.append("else")
            out.extend(language.Node.indent(1, else_lines))

        out.append(endif_line)
        return out

class MIf(MIfExpr):
    def __init__(self, condition: MExpr, *body: MElement, **kw):
        super().__init__(f"if {str(condition).strip()}", *body, **kw)


class MIfDef(MIfExpr):
    def __init__(self, var: MVar, *body: MElement, **kw):
        super().__init__(f"ifdef {var.name}", *body, **kw)


class MIfNDef(MIfExpr):
    def __init__(self, var: MVar, *body: MElement, **kw):
        super().__init__(f"ifndef {var.name}", *body, **kw)


class MIfEq(MIfExpr):
    def __init__(self, a: MExpr, b: MExpr, *body: MElement, **kw):
        super().__init__(f"ifeq ({a},{b})", *body, **kw)


class MIfNEq(MIfExpr):
    def __init__(self, a: MExpr, b: MExpr, *body: MElement, **kw):
        super().__init__(f"ifneq ({a},{b})", *body, **kw)


# ===== define / endef =====

class MDefine(language.Block[MElement]):
    """
    Multi-line define / endef macro:

        define FOO
            ...
        endef

    `name` must be an MVar (only `name.name` is used, not $(NAME)).
    """

    def __init__(self, name: MVar, *body: MElement):
        if not isinstance(name, MVar):
            raise TypeError(f"Macro name must be MVar, got {type(name).__name__}")
        macro = name.name.strip()
        if not macro:
            raise ValueError("Macro name cannot be empty")

        begin = language.Text(f"define {macro}")
        end = language.Text("endef")

        super().__init__(
            begin=begin,
            end=end,
            margin=None,
            inner=False,
            outer=False,
        )
        self.extend(body)


# ===== Commands =====

class MCommand(language.Text):
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


class MShellCommand(MCommand):
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

class MRule(language.Block[MCommand]):
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
            begin=language.Text(header),
            end=None,
            margin=None,
            inner=True,
            outer=False,
        )


class MPhony(MRule):
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
