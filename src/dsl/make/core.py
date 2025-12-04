from enum import IntFlag
import re
from typing import Iterator, List, Optional, Union

from dsl import TextNode, WordsNode, Node, Line
from dsl.container import NodeStack, SimpleNodeStack
from dsl.content import BlankLineNode
from dsl.node import SupportsStr
from .var import MExpr

MElement = Node

class Makefile(NodeStack[MElement]):
    MARGIN:Optional[Node]=BlankLineNode()

    def __init__(self,*elements:MElement):
        super().__init__(*elements,margin=Makefile.MARGIN)

class MList(SimpleNodeStack[MElement]):
    pass

class MComment(TextNode):
    def __init__(self, text: str):
        super().__init__(f"# {text}" if text else "#")

class MFlag(IntFlag):
    """
    Bitmask of make command flags:

      IGNORE_ERRORS -> '-'
      SILENT        -> '@'
      ALWAYS        -> '+'

    - You can combine them with | or +:
        MFlag.SILENT | MFlag.IGNORE_ERRORS
        MFlag.SILENT + MFlag.ALWAYS

    - str(flag) renders the prefix string, for example:
        str(MFlag.SILENT)                      -> '@'
        str(MFlag.IGNORE_ERRORS | MFlag.SILENT)-> '-@'
        str(MFlag.NONE)                        -> ''
    """

    NONE = 0
    IGNORE_ERRORS = 1  # '-'
    SILENT = 2         # '@'
    ALWAYS = 4         # '+'

    def __str__(self) -> str:
        s = ""
        if self & MFlag.IGNORE_ERRORS:
            s += "-"
        if self & MFlag.SILENT:
            s += "@"
        if self & MFlag.ALWAYS:
            s += "+"
        return s


class MLine(MElement):
    """
    Base Makefile line that carries an MFlag.

    Concrete subclasses also inherit from a content node type
    such as TextNode or WordsNode to define how they *produce* lines.

    MLine then decorates rendering by injecting the prefix in front of
    the first rendered line.
    """

    def __init__(self, flags: MFlag = MFlag.NONE) -> None:
        # Node.__init__ will be called by TextNode / WordsNode in subclasses.
        self._flags: MFlag = flags
        self._prefix: str = str(flags)

    @property
    def flags(self) -> MFlag:
        return self._flags

    @property
    def prefix(self) -> str:
        """
        Prefix string built from flags, for example '@', '-@', '+', or ''.
        """
        return self._prefix

    @property
    def silent(self) -> bool:
        return bool(self._flags & MFlag.SILENT)

    @property
    def ignore_errors(self) -> bool:
        return bool(self._flags & MFlag.IGNORE_ERRORS)

    @property
    def always(self) -> bool:
        return bool(self._flags & MFlag.ALWAYS)

    def render(self, level: int = 0) -> Iterator[Line]:
        """
        Decorate the underlying node's rendering by:
          - prepending the prefix to the first emitted line
          - escaping all lines except the last one with a trailing backslash
        """
        it = super().render(level)
        prev = next(it, None)
        if prev is None:
            return

        # Apply prefix to the very first line
        first_value = self._prefix + prev.value if self._prefix else prev.value
        prev = Line(prev.level, first_value)

        for ln in it:
            # prev is not the last line any more, so escape it if non empty
            value = prev.value + " \\" if prev.value else prev.value
            yield Line(prev.level, value)
            prev = ln

        # Last line: no backslash
        yield prev



class MText(MLine, TextNode):
    """
    Simple text line that can wrap either a raw string or an MExpr.

    IMPORTANT:
      MText no longer touches the prefix directly.
      It renders its text via TextNode, and MLine.render automatically
      injects the prefix on the first line.
    """

    def __init__(self, *text: SupportsStr, flags: MFlag = MFlag.NONE) -> None:
        MLine.__init__(self, flags=flags)
        TextNode.__init__(self, *(str(val) for val in text))


class MCommand(MLine, WordsNode):
    """
    Shell-style make recipe command with structured `name` and `args`.

        MCommand("echo", "hello world", "$(VAR)")
        MCommand(MExpr("$(CC)"), MExpr("$(CFLAGS)"), "-o", "app", "main.o")

    - `name` and `args` are stored raw (str or MExpr)
    - Escaping is only applied when rendering `words()`
    - `flags` is an MFlag; the resulting prefix is injected in render()
      via MLine, before the first line.

    Rendering:

      words()   -> pure shell tokens (no prefix)
      lines()   -> single line with prefix at the beginning
      token     -> list(self.words())   (no prefix)
      command   -> next(self.lines())   (with prefix)
    """

    _SAFE_RE = re.compile(r"[A-Za-z0-9_\-./:]+$")

    def __init__(
        self,
        name: SupportsStr,
        *args: SupportsStr,
        flags: MFlag = MFlag.NONE,
    ) -> None:
        if isinstance(name, str) and not name:
            raise ValueError("MCommand requires a non empty command name")

        MLine.__init__(self, flags=flags)
        WordsNode.__init__(self, sep=" ")

        self._name: SupportsStr = name
        self._args: List[SupportsStr] = list(args)

    # ---- raw API ----

    @property
    def name(self) -> SupportsStr:
        return self._name

    @property
    def args(self) -> List[SupportsStr]:
        return list(self._args)

    # ---- escaping helpers ----

    @classmethod
    def _needs_quoting(cls, token: str) -> bool:
        if token == "":
            return True
        return cls._SAFE_RE.fullmatch(token) is None

    @staticmethod
    def _escape_token(token: str) -> str:
        """
        Shell escape a string using single quotes, handling embedded
        single quotes in the standard POSIX way:

            foo'bar -> 'foo'"'"'bar'
        """
        if token == "":
            return "''"
        parts = token.split("'")
        return "'" + "'\"'\"'".join(parts) + "'"

    def _format_arg(self, arg: SupportsStr) -> str:
        if isinstance(arg, MExpr):
            # Insert make expression as-is, e.g. $(CC) or $(CFLAGS)
            return str(arg)
        if isinstance(arg, str):
            return self._escape_token(arg) if self._needs_quoting(arg) else arg
        raise TypeError("command args must be str or MExpr")

    # ---- WordsNode API ----

    def __iter__(self) -> Iterator[str]:
        """
        Pure shell tokens, without make prefix.
        Prefix is injected at render time by MLine.render.
        """
        yield self._format_arg(self._name)
        for a in self._args:
            yield self._format_arg(a)

    # ---- convenience properties ----

    @property
    def token(self) -> List[str]:
        """
        Fully formatted tokens WITHOUT prefixes.
        This is the "pure shell" view.
        """
        return list(self)

    @property
    def command(self) -> str:
        """
        Single formatted command line (first line from lines()),
        including the make prefix.
        """
        it = self.lines()
        return next(it, "")
