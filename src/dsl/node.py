from abc import ABC, abstractmethod
from typing import Iterable, Iterator, List, NamedTuple, Optional, Protocol, Self, Set, Tuple

class SupportsStr(Protocol):
    def __str__(self) -> str:
        ...

class Line(NamedTuple):
    level: int
    value: str

    INDENT = "\t"  # or "    " if you prefer spaces

    def __str__(self) -> str:
        lvl = max(0, int(self.level))
        if not self.value or lvl <= 0:
            return self.value
        return self.INDENT * lvl + self.value


# ========= Core node =========

class Node(ABC):
    def __init__(self) -> None:
        self._tags: Set[str] = set()

    # ---- core API ----

    @abstractmethod
    def render(self, level: int = 0) -> Iterator[Line]:
        ...

    def __str__(self) -> str:
        return "\n".join(str(line) for line in self.render())

    # ---- tag feature ----

    @property
    def tags(self) -> Tuple[str, ...]:
        return tuple(self._tags)

    def addTags(self, *tags: str) -> Self:
        self._tags.update(tags)
        return self

    def find(self, *tags: str) -> Iterator["Node"]:
        """
        Depth first search that yields nodes having all given tags.

        Example:
            for node in root.find("warning", "deprecated"):
                ...
        """
        if tags and all(t in self._tags for t in tags):
            yield self


class NullNode(Node):
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
        return 
        yield

    def __repr__(self) -> str:
        return "NullNode()"


nullNode = NullNode()

class IterableNode[TItem](Node,ABC):

    @abstractmethod
    def __iter__(self)->Iterator[TItem]:
        raise NotImplementedError

class ListNode[TItem](IterableNode[TItem]):
    """
    Generic Node backed by a list of items.
    Can be reused for nodes that contain other Nodes, strings, etc.
    """

    def __init__(self, *items: TItem) -> None:
        super().__init__()
        self._items: List[TItem] = list(items)

    # ---- mutation ----

    def append(self, item: TItem) -> Self:
        self._items.append(item)
        return self

    __iadd__ = append

    def extend(self, items: Iterable[TItem]) -> Self:
        self._items.extend(items)
        return self

    # ---- algebra ----

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

    # ---- sequence protocol ----

    def __getitem__(self, index: int) -> TItem:
        return self._items[index]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[TItem]:
        return iter(self._items)


class LevelNode(Node):
    def __init__(self,level:int):
        super().__init__()
        self._level=level

    @property
    def level(self):
        return self._level
