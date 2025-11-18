from __future__ import annotations

from abc import ABC, abstractmethod
from copy import copy
from typing import Generic, Iterable, List, Optional, Self, TypeVar, cast
from .typing_utils import resolve_generic_type_arg


# ========= Core node =========

class Node(ABC):
    @property
    @abstractmethod
    def lines(self) -> List[str]:
        raise NotImplementedError

    def __str__(self) -> str:
        return "\n".join(self.lines)


class IndentedNode(Node):
    TAB = "\t"

    def __init__(self, child: Node, level: int = 1):
        if not isinstance(child, Node):
            raise TypeError("child must be a Node")
        self._child = child
        self._level = max(0, int(level))

    @classmethod
    def _indent_line(cls, line: str, level: int) -> str:
        if not line:
            return ""
        return cls.TAB * level + line

    @classmethod
    def indent(cls, level: int, lines: List[str]) -> List[str]:
        if level <= 0:
            return list(lines)
        return [cls._indent_line(line, level) for line in lines]

    @property
    def child(self) -> Node:
        return self._child

    @property
    def level(self) -> int:
        return self._level

    @property
    def lines(self) -> List[str]:
        return self.indent(self._level, self._child.lines)


# ========= Null node =========

class NullNode(Node):
    """
    Singleton node that renders to nothing.
    Used instead of None wherever a Node is required but empty output is desired.
    """

    _instance: Optional["NullNode"] = None

    def __new__(cls) -> "NullNode":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def instance(cls) -> "NullNode":
        return cls()

    @property
    def lines(self) -> List[str]:
        return []

    def __repr__(self) -> str:
        return "NullNode()"


NULL = NullNode.instance()


# ========= Leaf nodes =========

class Text(Node):
    def __init__(self, text: str):
        self._text = text

    @property
    def lines(self) -> List[str]:
        return [self._text]

    @property
    def text(self) -> str:
        return self._text


class BlankLine(Node):
    """Vertical space: N empty lines."""

    def __init__(self, lines: int = 1):
        self._lines = max(0, int(lines))

    @property
    def lines(self) -> List[str]:
        return [""] * self._lines


# ========= SimpleStack (no margins) =========

TChild = TypeVar("TChild", bound="Node")
TExpected = TypeVar("TExpected", bound="Node")


class SimpleStack(Node, Generic[TChild]):
    """
    Simple vertical container without margins.
    Renders children one after another in order.
    """

    def __init__(self, *children: TChild):
        self._children: List[TChild] = []
        self._child_type: type = resolve_generic_type_arg(self, index=0, expected=Node)
        self.extend(children)

    # ---- configuration ----

    @property
    def child_type(self) -> type[Node]:
        return self._child_type

    @property
    def children(self) -> tuple[TChild, ...]:
        return tuple(self._children)

    # ---- helpers ----

    @staticmethod
    def ensure_type(value: object, expected: type[TExpected]) -> TExpected:
        """
        Runtime type guard that returns value as the expected subclass type.
        """
        if not isinstance(value, expected):
            raise TypeError(
                f"Expected {expected.__name__}, got {type(value).__name__}"
            )
        return cast(TExpected, value)

    # ---- mutation ----

    def append(self, child: TChild) -> Self:
        checked_child = self.ensure_type(child, self._child_type)
        self._children.append(checked_child)
        return self

    __iadd__ = append

    def extend(self, children: Iterable[TChild]) -> Self:
        for c in children:
            self.append(c)
        return self

    # ---- algebra ----

    def __imul__(self, n: int) -> Self:
        if not isinstance(n, int):
            raise TypeError("Repetition factor must be an int")

        if n <= 0:
            self._children.clear()
            return self

        if n == 1 or not self._children:
            return self

        self._children *= n
        return self

    repeat = __imul__

    def __mul__(self, n: int) -> Self:
        if not isinstance(n, int):
            return NotImplemented

        if n <= 0:
            new = copy(self)
            new._children = []
            return new

        new = copy(self)
        new._children = list(self._children) * n
        return new

    __rmul__ = __mul__

    def __add__(self, other: Node) -> Self:
        if not isinstance(other, self._child_type):
            return NotImplemented
        new = copy(self)
        new._children = list(self._children)
        new.append(other)  # type: ignore[arg-type]
        return new

    def __getitem__(self, index: int) -> TChild:
        return self._children[index]

    def __len__(self) -> int:
        return len(self._children)

    def __iter__(self):
        yield from self._children

    # ---- layout (vertical) ----

    @property
    def lines(self) -> List[str]:
        out: List[str] = []
        for node in self:
            out.extend(node.lines)
        return out


# ========= Stack with margins =========

class Stack(SimpleStack[TChild]):
    """
    Vertical container with optional inner / outer margin nodes.

      inner=NULL, outer=NULL -> c0, c1, c2
      inner=X,    outer=NULL -> c0, X, c1, X, c2
      inner=NULL, outer=Y    -> Y, c0, c1, c2, Y
      inner=X,    outer=Y    -> Y, c0, X, c1, X, c2, Y
    """

    def __init__(
        self,
        *children: TChild,
        inner: Node = NULL,
        outer: Node = NULL,
    ):
        super().__init__(*children)
        self._inner: Node = self.ensure_type(inner, Node)
        self._outer: Node = self.ensure_type(outer, Node)

    @property
    def inner(self) -> Node:
        return self._inner

    @property
    def outer(self) -> Node:
        return self._outer

    def set_margins(
        self,
        inner: Node = NULL,
        outer: Node = NULL,
    ) -> Self:
        self._inner = self.ensure_type(inner, Node)
        self._outer = self.ensure_type(outer, Node)
        return self

    def iter_with_margin(self, *nodes: Node):
        """
        Core margin logic, reused by __iter__ and by subclasses.

        Uses this stack's inner and outer nodes and inserts them around
        and between the given nodes.
        """
        seq: List[Node] = list(nodes)
        if not seq:
            return

        inner = self._inner
        outer = self._outer

        # Outer before
        yield outer

        if len(seq) > 1:
            for n in seq[:-1]:
                yield n
                yield inner
            # Last element
            yield seq[-1]
        else:
            # Single element
            yield seq[0]

        # Outer after
        yield outer

    def __iter__(self):
        # Default: margins around and between children
        yield from self.iter_with_margin(*self._children)


# ========= Word-aligned stack =========

class WordAlignedStack(Stack[TChild]):
    """
    Align children on word boundaries.

    For each child:
    - Join its lines with spaces.
    - Split on whitespace into words.
    Columns are sized by the widest word in each column.
    Only existing words are modified, then each row is joined with spaces.

    `limit` controls the maximum number of columns to align (None = no limit).
    """

    def __init__(
        self,
        *children: TChild,
        inner: Node = NULL,
        outer: Node = NULL,
        limit: Optional[int] = None,
    ):
        super().__init__(*children, inner=inner, outer=outer)
        self._limit: Optional[int] = limit

    @property
    def limit(self) -> Optional[int]:
        return self._limit

    @property
    def lines(self) -> List[str]:
        rows: List[List[str]] = []
        widths: List[int] = []

        # Pass 1: collect rows and compute max width per column
        for node in self:
            raw = " ".join(line.rstrip() for line in node.lines).strip()
            words = raw.split() if raw else []
            rows.append(words)

            for i, w in enumerate(words):
                if self._limit is not None and i >= self._limit:
                    break
                lw = len(w)
                if i == len(widths):
                    widths.append(lw)
                elif lw > widths[i]:
                    widths[i] = lw

        if not rows:
            return []

        # Pass 2: pad existing words, then join
        out: List[str] = []
        for words in rows:
            n = min(len(words), len(widths))
            if n > 1:
                for i in range(n - 1):
                    w = words[i]
                    pad = widths[i] - len(w)
                    if pad > 0:
                        words[i] = w + " " * pad

            out.append(" ".join(words) if n else "")

        return out


# ========= Block =========

TBegin = TypeVar("TBegin", bound="Node")
TEnd = TypeVar("TEnd", bound="Node")


class Block(Stack[TChild], Generic[TChild, TBegin, TEnd]):
    """
    Begin/end wrapper with indented inner content.

    Layout:

      outer, begin, inner+children, end, outer
    """

    def __init__(
        self,
        begin: TBegin,
        end: TEnd,
        *children: TChild,
        inner: Node = NULL,
        outer: Node = NULL,
    ):
        # Resolve type parameters for begin and end (if generics are used)
        self._begin_type: type = resolve_generic_type_arg(self, index=1, expected=Node)
        self._end_type: type = resolve_generic_type_arg(self, index=2, expected=Node)

        # Type-check begin / end according to TBegin / TEnd
        self._begin: TBegin = self.ensure_type(begin, self._begin_type)
        self._end: TEnd = self.ensure_type(end, self._end_type)

        super().__init__(*children, inner=inner, outer=outer)

    def __iter__(self):
        # Build the virtual sequence: begin, indented children, end
        nodes: List[Node] = []
        nodes.append(self._begin)
        nodes.extend(IndentedNode(child, 1) for child in self.children)
        nodes.append(self._end)

        # Let Stack handle insertion of inner/outer margins
        yield from self.iter_with_margin(*nodes)

    @property
    def begin(self) -> TBegin:
        return self._begin

    @property
    def end(self) -> TEnd:
        return self._end

    def toStack(self) -> Stack[TChild]:
        """
        Just a typed cast from Block[TChild, TBegin, TEnd] to Stack[TChild].

        At runtime this is still the same object and still behaves like a Block
        (Block.__iter__ is used), but type checkers will see it as a Stack.
        """
        return cast(Stack[TChild], self)
