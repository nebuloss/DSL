"""
Core node abstraction — the rendering pipeline.

Every piece of generated text is a Node.  Nodes form a tree; the root is
rendered by calling  str(node)  which triggers  node.render(level=0).

Rendering pipeline
──────────────────
render(level) → Iterator[Line]

Line is a (level, text) pair.  Keeping the indent level separate from the
text means a parent container can shift the entire subtree just by calling
child.render(level + offset) — no string manipulation needed.

__str__ joins all Lines, applying indentation at the last moment:
    Line(level=2, value="foo")  →  "\t\tfoo"

Why not yield strings directly?
  IndentedNode needs to increment the level of every line its child emits.
  Passing integers is cheaper than parsing and re-prepending tab strings.

NullNode
────────
A singleton that renders to nothing.  Used as a default "no margin" /
"no separator" so call-sites never need to check for None.

Tags
────
Nodes carry an optional set of string tags (addTags / find).  find() does
a depth-first search and yields every node that has all the requested tags.
Useful for post-hoc inspection of generated trees.
"""
from abc import ABC, abstractmethod
from typing import Iterable, Iterator, List, NamedTuple, Optional, Protocol, Self, Set, Tuple

class SupportsStr(Protocol):
    def __str__(self) -> str:
        ...

class Line(NamedTuple):
    level: int
    value: str

    INDENT = "\t"

    def __str__(self) -> str:
        lvl = max(0, int(self.level))
        if not self.value or lvl <= 0:
            return self.value
        return self.INDENT * lvl + self.value


# ── Core node ────────────────────────────────────────────────────────────────

class Node(ABC):
    def __init__(self) -> None:
        self._tags: Set[str] = set()

    @abstractmethod
    def render(self, level: int = 0) -> Iterator[Line]:
        ...

    def __str__(self) -> str:
        return "\n".join(str(line) for line in self.render())

    # ── Tags ──────────────────────────────────────────────────────────────

    @property
    def tags(self) -> Tuple[str, ...]:
        return tuple(self._tags)

    def addTags(self, *tags: str) -> Self:
        self._tags.update(tags)
        return self

    def find(self, *tags: str) -> Iterator["Node"]:
        """Depth-first search: yield nodes that carry ALL of the given tags."""
        if tags and all(t in self._tags for t in tags):
            yield self


# ── NullNode ─────────────────────────────────────────────────────────────────

class NullNode(Node):
    """Singleton that emits no lines.

    Used instead of None wherever a Node is required but empty output is
    desired (e.g. the default margin in NodeStack).  The singleton guarantee
    means  `margin is nullNode`  is a cheap identity test.
    """

    _instance: Optional["NullNode"] = None

    def __new__(cls) -> "NullNode":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            Node.__init__(cls._instance)
        return cls._instance

    def render(self, level: int = 0) -> Iterator[Line]:
        return
        yield  # makes this a generator without producing any values

    def __repr__(self) -> str:
        return "NullNode()"


nullNode = NullNode()


# ── Generic list-backed node ──────────────────────────────────────────────────

class IterableNode[TItem](Node, ABC):

    @abstractmethod
    def __iter__(self) -> Iterator[TItem]:
        raise NotImplementedError

class ListNode[TItem](IterableNode[TItem]):
    """Node backed by a mutable list of items.

    Subclasses decide what TItem means (other Nodes, strings, …) and how to
    render the list via render().  Mutation after construction is intentional:
    KOption uses it to append defaults/depends lazily.
    """

    def __init__(self, *items: TItem) -> None:
        super().__init__()
        self._items: List[TItem] = list(items)

    def append(self, item: TItem) -> Self:
        self._items.append(item)
        return self

    __iadd__ = append

    def extend(self, items: Iterable[TItem]) -> Self:
        self._items.extend(items)
        return self

    def __imul__(self, n: int) -> Self:
        if not isinstance(n, int):
            raise TypeError("Repetition factor must be an int")
        if n <= 0:
            self._items.clear()
            return self
        if n == 1 or not self._items:
            return self
        self._items *= n
        return self

    repeat = __imul__

    def __getitem__(self, index: int) -> TItem:
        return self._items[index]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[TItem]:
        return iter(self._items)


# ── Level-aware node ──────────────────────────────────────────────────────────

class LevelNode(Node):
    """Mixin that stores an explicit indentation level.

    Used by IndentedNode (relative offset) and FixedNode (absolute level).
    """
    def __init__(self, level: int):
        super().__init__()
        self._level = level

    @property
    def level(self):
        return self._level
