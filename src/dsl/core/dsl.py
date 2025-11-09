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
        return [cls._indent_line(line, level) for line in lines]

    @abstractmethod
    def render(self) -> List[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def width(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def height(self) -> int:
        raise NotImplementedError

    def __str__(self) -> str:
        return "\n".join(self.render())


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


class Container(Node, Generic[T], ABC):
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

class VStack(Container[T]):
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

class HStack(Container[T]):
    def render(self) -> List[str]:
        items = list(self)
        if not items:
            return []

        # Wrap each item in a Box so all columns align by height
        boxes: List[Box[Node]] = []
        for node in items:
            b: Box[Node] = Box()
            b.append(node)
            boxes.append(b)

        max_height = max(b.height for b in boxes)
        for b in boxes:
            b.resize(height=max_height)

        cols = [b.render() for b in boxes]

        out: List[str] = []
        for row in range(max_height):
            out.append("".join(col[row] for col in cols))
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
