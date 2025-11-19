#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Dict, List, Literal, Optional, Union

from dsl import Node,Stack,SimpleStack,BlankLine,Text,Block
from dsl.lang import NULL_NODE, NullNode
from .var import MExpr

MElement = Node

class Makefile(Stack[MElement]):
    MARGIN:Optional[Node]=BlankLine()

    def __init__(self,*elements:MElement):
        super().__init__(*elements,inner=Makefile.MARGIN)

class MList(SimpleStack[MElement]):
    pass

# ===== Comments and banners =====

class MComment(Text):
    def __init__(self, text: str):
        super().__init__(f"# {text}" if text else "#")


# ===== Commands =====

class MCommand(Text):
    """
    Make recipe command line.

    Prefix semantics:

      '-'  : ignore errors for this command
      '@'  : do not echo this command (unless overridden by -n etc.)
      '+'  : always execute, even with -n/-q/-t

    Any prefix characters already present in `line` are stripped and
    replaced by the canonical prefix built from the flags.

    The `.command` property returns the execution line with all prefixes
    removed.
    """

    # Mapping from flag name to prefix char
    _FLAG_CHAR: Dict[str, str] = {
        "ignore_errors": "-",
        "silent": "@",
        "always": "+",
    }

    # ---- helpers ----

    @classmethod
    def _strip_prefix(cls, text: str) -> str:
        """
        Return the core part of the command with any leading prefix
        characters removed and leading whitespace stripped.
        """
        text = text.lstrip()
        prefix_chars = "".join(cls._FLAG_CHAR.values())
        i = 0
        while i < len(text) and text[i] in prefix_chars:
            i += 1
        core = text[i:].lstrip()
        return core

    def _set_prefix(
        self,
        *,
        silent: bool = False,
        ignore_errors: bool = False,
        always: bool = False,
    ) -> None:
        """
        Initialise internal flags from explicit args only.
        Existing prefixes in the original line are ignored.
        """
        self._flags: Dict[str, bool] = {
            "silent": bool(silent),
            "ignore_errors": bool(ignore_errors),
            "always": bool(always),
        }

    def _get_prefix(self) -> str:
        """
        Build canonical prefix string from internal flags.
        """
        parts: List[str] = []
        for name,value in self._FLAG_CHAR.items():
            if self._flags.get(name):
                parts.append(value)
        return "".join(parts)

    # ---- main API ----

    def __init__(
        self,
        line: str,
        *,
        silent: bool = False,
        ignore_errors: bool = False,
        always: bool = False,
    ):
        if not isinstance(line, str):
            raise TypeError("Command line must be a str")

        core = self._strip_prefix(line)
        self._set_prefix(
            silent=silent,
            ignore_errors=ignore_errors,
            always=always,
        )
        full_text = self._get_prefix() + core

        super().__init__(full_text)

    # ---- flags introspection ----

    @property
    def flags(self) -> Dict[str, bool]:
        # Treat as read-only from outside
        return self._flags

    @property
    def silent(self) -> bool:
        return self._flags["silent"]

    @property
    def ignore_errors(self) -> bool:
        return self._flags["ignore_errors"]

    @property
    def always(self) -> bool:
        return self._flags["always"]

    # ---- execution line (prefix stripped) ----

    @property
    def command(self) -> str:
        """
        Execution line as per spec:
        the command line with any prefix chars removed.
        """
        return self._strip_prefix(self.text)


class MShellCommand(MCommand):
    """
    Convenience wrapper to build a command line from arguments.

        MShellCommand("echo", "hello", "$(VAR)")
        MShellCommand(M.var("CC"), M.var("CFLAGS"), "-o", "app", "main.o")

    str args are shell-escaped only when needed.
    MExpr args are inserted as-is.

    Prefix flags:
      - silent=True        -> '@' prefix
      - ignore_errors=True -> '-' prefix
      - always=True        -> '+' prefix
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

    def __init__(
        self,
        *args: Union[str, MExpr],
        silent: bool = False,
        ignore_errors: bool = False,
        always: bool = False,
    ):
        if not args:
            raise ValueError("MShellCommand requires at least one argument")

        parts: List[str] = [self._format_arg(a) for a in args]
        line = " ".join(parts)

        super().__init__(
            line,
            silent=silent,
            ignore_errors=ignore_errors,
            always=always,
        )

# ===== Rules =====

class MRule(Block[MCommand,Text,NullNode]):
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
            Text(header),
            NULL_NODE,
            inner=None,
            outer=None
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

class MLine(Text):
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
