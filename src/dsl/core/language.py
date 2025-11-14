from __future__ import annotations

from abc import ABC, abstractmethod
from copy import copy
from typing import Generic, Iterable, List, Optional, Self, TypeVar, get_args


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
    def child(self):
        return self._child
    
    @property
    def level(self):
        return self._level

    @property
    def lines(self) -> List[str]:
        return self.indent(self._level, self._child.lines)

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
        inner: Optional[Node] = None,
        outer: Optional[Node] = None
    ):

        self._children: List[T] = []
        self._child_type: type = self._resolve_child_type()
        self.set_margins(inner,outer)

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

    def set_margins(self, inner: Optional[Node]=None, outer:Optional[Node] = None) -> Self:
        if inner is not None and not isinstance(inner,Node):
            raise TypeError("inner margin must be a Node")
        if outer is not None and not isinstance(outer,Node):
            raise TypeError("outer margin must be a Node")

        self._inner = inner
        self._outer = outer
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

     # ---- margin helper ----

    def iter_with_margin(self, *nodes: Optional[Node]):
        """
        Core margin logic, reused by __iter__ and by subclasses.

        Uses this stack's inner and outer nodes (if not None) and inserts
        them around and between the given nodes:

        inner=None, outer=None -> c0, c1, c2
        inner=X,   outer=None  -> c0, X, c1, X, c2
        inner=None, outer=Y    -> Y, c0, c1, c2, Y
        inner=X,   outer=Y     -> Y, c0, X, c1, X, c2, Y
        """
        # Filter out None nodes first
        seq: List[Node] = [n for n in nodes if n is not None]
        if not seq:
            return
        
        inner = self._inner
        outer = self._outer

        # Outer before
        if outer is not None:
            yield outer

        for n in seq[:-1]:
            yield n
            if inner is not None:
                yield inner
        # Last element
        yield seq[-1]
        
        # Outer after
        if outer is not None:
            yield outer

    def __iter__(self):
        yield from self.iter_with_margin(*self._children)

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

    def __init__(self, inner:Optional[Node] = None, outer: Optional[Node] = None, limit:Optional[int]=None):
        super().__init__(inner, outer)
        self._limit:Optional[int]=limit

    @property
    def limit(self):
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
                lw = len(w)
                if self._limit is not None and i>=self._limit:
                    break
                if i == len(widths):
                    widths.append(lw)
                elif lw > widths[i]:
                    widths[i] = lw

        if not rows:
            return []

        # Pass 2: pad existing words, then join
        out: List[str] = []
        for words in rows:
            n = min(len(words),len(widths))
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
        inner: Optional[Node] = None,
        outer: Optional[Node] = None
    ):
        if begin is not None and not isinstance(begin, Node):
            raise TypeError("begin must be a Node or None")
        if end is not None and not isinstance(end, Node):
            raise TypeError("end must be a Node or None")

        self._begin = begin
        self._end = end

        # inner / outer here drive margins between begin, children, end
        super().__init__(inner,outer)

    def __iter__(self):
        yield from self.iter_with_margin(self._begin,*(IndentedNode(child,1) for child in self.children),self._end)
