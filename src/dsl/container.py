"""
Container nodes — nodes that hold other Nodes.

Hierarchy
─────────
ContainerNode[T]           — base: render by delegating to children
  SimpleNodeStack[T]       — ordered list of children, no extras
    NodeStack[T]           — adds an optional margin node between children
      NodeBlock[T, Begin]  — prepends a begin node; children are indented
        DelimitedNodeBlock — also appends an end node

IndentedNode vs FixedNode
──────────────────────────
Both wrap a single child and override render():

  IndentedNode(child, level=1)  →  child.render(parent_level + 1)
    The offset is *relative*: the child shifts by `level` tabs on top of
    whatever the parent passes in.  This is the standard case for bodies.

  FixedNode(child, level=0)     →  child.render(self.level)
    The level is *absolute*: ignores the parent context entirely.
    Used for Makefile keywords (ifdef, endif, …) that must always appear
    at column 0 regardless of nesting depth.

NodeBlock composition
──────────────────────
NodeBlock stores children in its ListNode._items.  __iter__ yields:

    begin
    margin  (usually nullNode → nothing)
    IndentedNode(child0, level)
    margin
    IndentedNode(child1, level)
    …

When ContainerNode.render(lvl) iterates this, each item's own render(lvl)
is called.  IndentedNode bumps the level so the body is indented relative
to the header.  The begin node renders at the current level (no extra indent).
"""
from typing import Iterable, Iterator
from dsl.node import IterableNode, LevelNode, Line, ListNode, Node, nullNode

class ContainerNode[TChild: Node](IterableNode[TChild]):
    """Renders by chaining render() of every child at the same level."""

    def empty(self) -> bool:
        return next(iter(self), None) is None

    def render(self, level: int = 0) -> Iterator[Line]:
        for child in self:
            yield from child.render(level)

    def find(self, *tags) -> Iterator[Node]:
        # Search self first, then recurse into children.
        yield from super().find(*tags)
        for child in self:
            yield from child.find(*tags)

class SingleContainerNode[TChild: Node](ContainerNode[TChild]):
    """Container with exactly one child."""
    def __init__(self, child: TChild):
        ContainerNode.__init__(self)
        self._child = child

    @property
    def child(self) -> TChild:
        return self._child

    def __iter__(self) -> Iterator[TChild]:
        yield self.child

class IndentedNode[TChild: Node](SingleContainerNode[TChild], LevelNode):
    """Renders its child at  parent_level + self.level  (relative offset)."""
    def __init__(self, child: TChild, level: int = 1):
        SingleContainerNode.__init__(self, child)
        LevelNode.__init__(self, level)

    def render(self, level: int = 0) -> Iterator[Line]:
        yield from self.child.render(level + self.level)

class FixedNode[TChild: Node](SingleContainerNode[TChild], LevelNode):
    """Renders its child at self.level regardless of the parent level."""
    def __init__(self, child: TChild, level: int = 0):
        SingleContainerNode.__init__(self, child)
        LevelNode.__init__(self, level)

    def render(self, level: int = 0) -> Iterator[Line]:
        yield from self.child.render(self.level)

class SimpleNodeStack[TChild: Node](ListNode[TChild], ContainerNode[TChild]):
    """Ordered list of children rendered consecutively, no separators."""
    pass

class NodeStack[TChild: Node](SimpleNodeStack[TChild]):
    """Children separated by an optional margin node.

    The margin is inserted *between* children (not before the first or after
    the last), making it easy to add blank lines between Makefile sections.

    With margin=BlankLineNode():  child0, blank, child1, blank, child2
    With margin=nullNode:         child0, child1, child2  (default)
    """

    def __init__(self, *children: TChild, margin: Node = nullNode):
        super().__init__(*children)
        self._margin: Node = margin

    def inner(self) -> Iterator[Node]:
        """The raw children, without any margin."""
        yield from SimpleNodeStack.__iter__(self)

    def iter_with_margin(self, *nodes: Node) -> Iterator[Node]:
        """Yield nodes with self._margin inserted between each pair."""
        it = iter(nodes)
        first = next(it, None)
        if first is None:
            return
        yield first
        for child in it:
            yield self._margin
            yield child

    def __iter__(self) -> Iterator[Node]:
        yield from self.iter_with_margin(*self.inner())

class NodeBlock[TChild: Node, TBegin: Node](NodeStack[TChild]):
    """A header (begin) node followed by indented children.

    Rendered as:
        <begin>
        <margin>
        <indent> child0
        <margin>
        <indent> child1
        …
    """

    def __init__(
        self,
        begin: TBegin,
        *children: TChild,
        margin: Node = nullNode,
        level: int = 1,
    ):
        self._begin: TBegin = begin
        self._level = level
        super().__init__(*children, margin=margin)

    @property
    def begin(self) -> TBegin:
        return self._begin

    def inner(self) -> Iterator[Node]:
        """Children wrapped in IndentedNode so they render one level deeper."""
        for node in super().inner():
            yield IndentedNode(node, self._level)

    def __iter__(self) -> Iterable[Node]:
        # begin is at the current level; children are indented below it.
        yield from self.iter_with_margin(self.begin, *self.inner())


class DelimitedNodeBlock[TChild: Node, TBegin: Node, TEnd: Node](NodeBlock[TChild, TBegin]):
    """NodeBlock with an explicit end node appended after all children.

    Used for blocks that have matching open/close keywords:
      Makefile:  ifdef … endif,  define … endef
      Kconfig:   menu … endmenu,  if … endif,  choice … endchoice
    """
    def __init__(
        self,
        begin: TBegin,
        end: TEnd,
        *children: TChild,
        margin=nullNode,
        level: int = 1,
    ):
        super().__init__(begin, *children, margin=margin, level=level)
        self._end: TEnd = end

    @property
    def end(self) -> TEnd:
        return self._end

    def __iter__(self) -> Iterator[Node]:
        yield from self.iter_with_margin(self.begin, *self.inner(), self.end)
