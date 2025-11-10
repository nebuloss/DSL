from __future__ import annotations

from abc import ABC, abstractmethod
from copy import copy
from typing import Generic, Iterable, List, Optional, Self, TypeVar, get_args


# ========= Core node =========

# ========= Core node =========

class Node(ABC):
    TAB = "\t"

    def __init__(self, width: Optional[int] = None, height: Optional[int] = None):
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        self.resize(width=width, height=height)

    @classmethod
    def _indent_line(cls, line: str, level: int) -> str:
        if not line:
            return ""
        return cls.TAB * level + line

    @classmethod
    def indent(cls, level: int, lines: List[str]) -> List[str]:
        return [cls._indent_line(line, level) for line in lines]

    @abstractmethod
    def render(self) -> List[str]:
        raise NotImplementedError

    @staticmethod
    def _fit_lines(lines: List[str], width: Optional[int], height: Optional[int]) -> List[str]:
        if height is not None:
            if len(lines) > height:
                lines = lines[:height]
            else:
                lines = lines + [""] * (height - len(lines))

        target = width if width is not None else max((len(l) for l in lines), default=0)

        out: List[str] = []
        for l in lines:
            ln = len(l)
            if width is not None and ln > target:
                out.append(l[:target])
            elif ln < target:
                out.append(l + " " * (target - ln))
            else:
                out.append(l)
        return out

    @property
    def lines(self) -> List[str]:
        return self._fit_lines(self.render(), self._width, self._height)

    # New: compute width and height together with a single render
    @property
    def size(self) -> tuple[int, int]:
        """Return (width, height) using explicit values if set, else compute the missing ones."""
        w = self._width
        h = self._height

        if w is not None and h is not None:
            return w, h

        nat = self.render()  # single render
        if w is None:
            w = max((len(line) for line in nat), default=0)
        if h is None:
            h = len(nat)

        return w, h


    @property
    def width(self) -> int:
        w, _ = self.size
        return w

    @property
    def height(self) -> int:
        _, h = self.size
        return h

    def resize(self, width: Optional[int] = None, height: Optional[int] = None) -> Self:
        if width is not None:
            self._width = max(0, int(width))
        if height is not None:
            self._height = max(0, int(height))
        return self

    def __str__(self) -> str:
        return "\n".join(self.lines)


# ========= Leaf nodes =========

class Text(Node):
    def __init__(self, text: str):
        self._text = text

    def render(self) -> List[str]:
        return [self._text]

    @property
    def width(self) -> int:
        return len(self._text)

    @property
    def height(self) -> int:
        return 1


class VSpace(Node):
    """Vertical space: N empty lines."""
    def __init__(self, lines: int = 1):
        self._lines = max(0, int(lines))

    def render(self) -> List[str]:
        return [""] * self._lines

    @property
    def width(self) -> int:
        return 0

    @property
    def height(self) -> int:
        return self._lines


class HSpace(Node):
    """Horizontal space: 1 line with N spaces."""
    def __init__(self, spaces: int = 1):
        self._spaces = max(0, int(spaces))

    def render(self) -> List[str]:
        return [" " * self._spaces]

    @property
    def width(self) -> int:
        return self._spaces

    @property
    def height(self) -> int:
        return 1


# ========= Base container =========

T = TypeVar("T", bound="Node")


class Stack(Node, Generic[T], ABC):
    """
    Generic container with optional margin insertion:

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
    def child_type(self)->type[Node]:
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
    
    def __getitem__(self,index:int) -> T:
        return self._children[index]
    
    def __len__(self) -> int:
        return len(self._children)

    @abstractmethod
    def render(self) -> List[str]:
        raise NotImplementedError

    @property
    def width(self) -> int:
        lines = self.render()
        return max((len(line) for line in lines), default=0)

    @property
    def height(self) -> int:
        return len(self.render())


# ========= Vertical stack =========

class VStack(Stack[T]):
    def render(self) -> List[str]:
        out: List[str] = []
        for node in self:
            out.extend(node.render())
        return out


# ========= Box (rectangular) =========

class Box(VStack[T]):
    """
    Rectangular view on vertical content.
    Pads or crops to (width, height) if provided.
    """

    def __init__(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        margin: Optional[Node] = None,
        inner: bool = True,
        outer: bool = False,
    ):
        self._width = int(width) if width is not None else None
        self._height = int(height) if height is not None else None
        super().__init__(margin=margin, inner=inner, outer=outer)

    def resize(self, width: Optional[int] = None, height: Optional[int] = None) -> Self:
        if width is not None:
            self._width = max(0, int(width))
        if height is not None:
            self._height = max(0, int(height))
        return self

    def render(self) -> List[str]:
        lines = super().render()

        # static height
        if self._height is not None:
            if len(lines) > self._height:
                lines = lines[: self._height]
            else:
                lines = lines + [""] * (self._height - len(lines))

        # target width
        natural = max((len(l) for l in lines), default=0)
        target = self._width if self._width is not None else natural

        out: List[str] = []
        for l in lines:
            if len(l) < target:
                out.append(l + " " * (target - len(l)))
            elif len(l) > target and self._width is not None:
                out.append(l[:target])
            else:
                out.append(l)
        return out

    @property
    def width(self) -> int:
        if self._width is not None:
            return self._width
        return super().width

    @property
    def height(self) -> int:
        if self._height is not None:
            return self._height
        return super().height


# ========= Horizontal stack =========

class HStack(Stack[T]):
    def render(self) -> List[str]:
        items = list(self)
        if not items:
            return []

        # 1) fix each child width to its current width
        widths: List[int] = []
        heights: List[int] = []
        for c in items:
            w, h = c.size   # single pass for both
            c.resize(width=w)
            widths.append(w)
            heights.append(h)

        # 2) compute max height
        row_h = max(heights) if heights else 0

        # 3) fix each child height to max height
        for c in items:
            c.resize(height=row_h)

        # 4) join
        if row_h == 0:
            return []
        cols = [c.lines for c in items]
        out: List[str] = []
        for r in range(row_h):
            out.append("".join(col[r] for col in cols))
        return out


# ========= Block =========

class Block(VStack[T]):
    """
    Begin / end wrapper with indented inner content.
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

    def render(self) -> List[str]:
        out: List[str] = []

        if self._begin is not None:
            out.extend(self._begin.render())

        inner_lines = super().render()
        out.extend(self.indent(1, inner_lines))

        if self._end is not None:
            out.extend(self._end.render())

        return out
