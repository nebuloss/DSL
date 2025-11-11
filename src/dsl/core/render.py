from __future__ import annotations

from abc import ABC, abstractmethod
from copy import copy
from typing import Generic, Iterable, List, Optional, Self, TypeVar, get_args


# ========= Core node =========

class Node(ABC):
    TAB = "\t"

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
    @abstractmethod
    def lines(self) -> List[str]:
        raise NotImplementedError

    def __str__(self) -> str:
        return "\n".join(self.lines)


# ========= Leaf nodes =========

class Text(Node):
    def __init__(self, text: str):
        self._text = text

    @property
    def lines(self) -> List[str]:
        return [self._text]


class BlankLine(Node):
    """Vertical space: N empty lines."""
    def __init__(self, lines: int = 1):
        self._lines = max(0, int(lines))

    @property
    def lines(self) -> List[str]:
        return [""] * self._lines


# ========= Base vertical stack =========

T = TypeVar("T", bound="Node")


class Stack(Node, Generic[T]):
    """
    Vertical container with optional margin insertion.

      inner=False, outer=False -> c0, c1, c2
      inner=True,  outer=False -> c0, m, c1, m, c2
      inner=False, outer=True  -> m, c0, c1, c2, m
      inner=True,  outer=True  -> m, c0, m, c1, m, c2, m
    """

    def __init__(
        self,
        margin: Optional[Node] = None,
        inner: bool = True,
        outer: bool = False,
    ):
        if margin is not None and not isinstance(margin, Node):
            raise TypeError("margin must be a Node or None")

        self._children: List[T] = []
        self._margin: Optional[Node] = margin
        self._inner: bool = bool(inner)
        self._outer: bool = bool(outer)
        self._child_type: type = self._resolve_child_type()

    # ---- typing helper ----

    def _resolve_child_type(self) -> type:
        orig = getattr(self, "__orig_class__", None)
        if orig is not None:
            args = get_args(orig)
            if args:
                t = args[-1]
                if isinstance(t, type) and issubclass(t, Node):
                    return t

        for base in getattr(type(self), "__orig_bases__", ()):
            args = get_args(base)
            if args:
                t = args[-1]
                if isinstance(t, type) and issubclass(t, Node):
                    return t

        return Node

    # ---- configuration ----

    @property
    def margin(self) -> Optional[Node]:
        return self._margin

    def set_margins(self, inner: bool = True, outer: bool = False) -> Self:
        self._inner = bool(inner)
        self._outer = bool(outer)
        return self

    @property
    def child_type(self) -> type[Node]:
        return self._child_type

    @property
    def children(self) -> tuple[T, ...]:
        return tuple(self._children)

    # ---- mutation ----

    def append(self, child: T) -> Self:
        if not isinstance(child, self._child_type):
            raise TypeError(
                f"Expected child of type {self._child_type.__name__}, "
                f"got {type(child).__name__}"
            )
        self._children.append(child)
        return self

    __iadd__ = append

    def extend(self, children: Iterable[T]) -> Self:
        for c in children:
            self.append(c)
        return self

    # ---- iteration with margins ----

    def __iter__(self):
        children = self._children
        if not children:
            return

        m = self._margin
        use_m = m is not None

        it = iter(children)
        first = next(it, None)
        if first is None:
            return

        if self._outer and use_m:
            yield m

        yield first

        for child in it:
            if self._inner and use_m:
                yield m
            yield child

        if self._outer and use_m:
            yield m

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
        new.append(other)
        return new

    def __getitem__(self, index: int) -> T:
        return self._children[index]

    def __len__(self) -> int:
        return len(self._children)

    # ---- layout (vertical) ----

    @property
    def lines(self) -> List[str]:
        out: List[str] = []
        for node in self:
            out.extend(node.lines)
        return out


# ========= Word-aligned stack =========

class WordAlignedStack(Stack[T]):
    """
    Align children on word boundaries.

    For each child:
    - Join its lines with spaces.
    - Split on whitespace into words.
    Columns are sized by the widest word in each column.
    Only existing words are modified, then each row is joined with spaces.
    """

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
            n = len(words)
            if n > 1:
                for i in range(n - 1):
                    w = words[i]
                    pad = widths[i] - len(w)
                    if pad > 0:
                        words[i] = w + " " * pad

            out.append(" ".join(words) if n else "")

        return out


# ========= Block =========

class Block(Stack[T]):
    """
    Begin/end wrapper with indented inner content.
    """

    def __init__(
        self,
        begin: Optional[Node] = None,
        end: Optional[Node] = None,
        margin: Optional[Node] = None,
        inner: bool = True,
        outer: bool = True,
    ):
        if begin is not None and not isinstance(begin, Node):
            raise TypeError("begin must be a Node or None")
        if end is not None and not isinstance(end, Node):
            raise TypeError("end must be a Node or None")

        self._begin = begin
        self._end = end
        super().__init__(margin=margin, inner=inner, outer=outer)

    @property
    def lines(self) -> List[str]:
        out: List[str] = []

        if self._begin is not None:
            out.extend(self._begin.lines)

        inner_lines = super().lines
        if inner_lines:
            out.extend(self.indent(1, inner_lines))

        if self._end is not None:
            out.extend(self._end.lines)

        return out
