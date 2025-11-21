# ========= Text node hierarchy =========

from abc import ABC
from typing import Iterable, Iterator, Optional, Tuple

from dsl.node import Line, Node


class ContentNode(Node, ABC):
    """
    Base class for leaf nodes with no children.
    Implements an empty iterator.
    """

    def __iter__(self) -> Iterable[Node]:
        # Leaf node: no children
        return iter(())


class NullNode(ContentNode):
    """
    Singleton node that renders to nothing.
    Used instead of None wherever a Node is required but empty output is desired.
    """

    _instance: Optional["NullNode"] = None

    def __new__(cls) -> "NullNode":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Explicitly call Node.__init__ once
            Node.__init__(cls._instance)
        return cls._instance

    def render(self, level: int = 0) -> Iterator[Line]:
        return iter(())

    def __repr__(self) -> str:
        return "NullNode()"


NULL_NODE = NullNode()

class BlankLineNode(ContentNode):
    """Vertical space: N empty lines."""

    def __init__(self, lines: int = 1) -> None:
        super().__init__()
        self._lines = max(0, int(lines))

    def render(self, level: int = 0) -> Iterable[Line]:
        for _ in range(self._lines):
            yield Line(level, "")



class GenericTextNode(ContentNode, ABC):
    """
    Base class for text nodes storing one or more raw string lines.
    Subclasses define how indentation is computed from `render(level)`.
    """

    def __init__(self, *lines: str) -> None:
        super().__init__()
        self._lines: Tuple[str, ...] = tuple(lines)

    @property
    def lines(self) -> Tuple[str, ...]:
        """Raw text lines (without indentation)."""
        return self._lines


class TextNode(GenericTextNode):
    """
    Default relative text node.
    Indentation level comes from `render(level)`.
    """

    def render(self, level: int = 0) -> Iterator[Line]:
        lvl = max(0, int(level))
        for value in self._lines:
            yield Line(lvl, value)


class FixedTextNode(GenericTextNode):
    """
    Text node with a fixed indentation level given at construction.
    Ignores the `level` argument of render().
    """

    def __init__(self, *lines: str, level: int = 0) -> None:
        super().__init__(*lines)
        self._fixed_level = max(0, int(level))

    @property
    def fixed_level(self) -> int:
        return self._fixed_level

    def render(self, level: int = 0) -> Iterator[Line]:
        lvl = self._fixed_level
        for value in self._lines:
            yield Line(lvl, value)

