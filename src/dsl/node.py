from abc import ABC, abstractmethod
from typing import Iterator, NamedTuple, Self, Set, Tuple

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
