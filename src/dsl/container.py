from abc import ABC, abstractmethod
from copy import copy
import re
from typing import Iterable, Iterator, List, Optional, Self

from dsl.content import NULL_NODE
from dsl.node import Line, Node

class ContainerNode(Node):
    """
    Base class for containers of child nodes with a single child type.

    - __class_getitem__ makes ContainerNode[T] (and subclasses) real subclasses
      whose __orig_bases__ contain GenericAlias(cls, (T,)).
    - child_type is resolved once in __init__ via resolve_generic_type_arg.
    - ensure_type / ensure_child_type centralise runtime checks.
    """

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def __iter__(self) -> Iterator["Node"]:
        """
        Iterate over direct children of this node.
        Leaf nodes should return an empty iterator.
        """
        raise NotImplementedError

    def empty(self) -> bool:
        return next(iter(self), None) is None
    
    def render(self, level: int = 0) -> Iterator[Line]:
        for child in self:
            yield from child.render(level)

class SimpleNodeStack[TChild: Node](ContainerNode):
    """
    Simple vertical container without margins.
    Renders children one after another in order.
    """

    def __init__(self, *children: TChild):
        super().__init__()
        self._children: List[TChild] = []
        self.extend(children)

    # ---- mutation ----

    def append(self, child: TChild) -> Self:
        self._children.append(child)
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
        if not isinstance(other, self.child_type):
            return NotImplemented
        new = copy(self)
        new._children = list(self._children)
        new.append(other)  # type: ignore[arg-type]
        return new

    def __getitem__(self, index: int) -> TChild:
        return self._children[index]

    def __len__(self) -> int:
        return len(self._children)

    def __iter__(self) -> Iterator[TChild]:
        # Structural iteration: just children, no decoration
        return iter(self._children)

    # ---- layout ----

class NodeStack[TChild: Node](SimpleNodeStack[TChild]):
    """
    Vertical container with optional inner / outer margin nodes.

      inner=NULL_NODE, outer=NULL_NODE -> c0, c1, c2
      inner=X,       outer=NULL_NODE   -> c0, X, c1, X, c2
      inner=NULL_NODE, outer=Y         -> Y, c0, c1, c2, Y
      inner=X,       outer=Y           -> Y, c0, X, c1, X, c2, Y
    """

    def __init__(
        self,
        *children: TChild,
        margin: Node = NULL_NODE,
    ):
        super().__init__(*children)
        self._margin:Node=margin

    @property
    def inner(self) -> Node:
        return self._inner

    @property
    def outer(self) -> Node:
        return self._outer
    
    def iter_with_margin(self,*nodes:Node)->Iterator[Node]:
        it=iter(nodes)
        first=next(it,None)
        if first is None:
            return
        
        yield first
        for child in it:
            yield self._margin
            yield child
    
    def __iter__(self)->Iterator[Node]:
        yield from self.iter_with_margin(*SimpleNodeStack.__iter__(self))

class IndentedNodeStack[TChild: Node](SimpleNodeStack[TChild]):
    def __init__(self, *children,level:int=1):
        super().__init__(*children)
        self._level=1

    def render(self, level = 0):
        yield from super().render(level+self._level)

class NodeBlock[TChild:Node,TBegin: Node](NodeStack[TChild]):

    def __init__(
        self,
        begin: TBegin,
        *children: TChild,
        margin:Node=NULL_NODE
    ):
        # Type-check begin / end according to TBegin / TEnd
        self._begin: TBegin = begin
        
        super().__init__(*children, margin=margin)

    @property
    def begin(self) -> TBegin:
        return self._begin

    def inner(self) -> IndentedNodeStack[Node]:
        return IndentedNodeStack(*NodeStack.__iter__(self))

    def __iter__(self) -> Iterable[Node]:
        yield from self.iter_with_margin(self.begin,self.inner()) 


class DelimitedNodeBlock[TChild:Node,TBegin: Node, TEnd:Node](NodeBlock[TChild,TBegin]):
    def __init__(self, begin: TBegin, end: TEnd, *children: TChild, margin = NULL_NODE):
        super().__init__(begin, *children, margin=margin)
        self._end: TEnd = end       # type: ignore[assignment]

    @property
    def end(self)->TEnd:
        return self._end
    
    def __iter__(self)->Iterator[Node]:
        yield from self.iter_with_margin(self.begin,NodeBlock.inner(self),self.end)

class WordAlignedStack[TChild: "Node"](NodeStack[TChild]):
    """
    Align children on word boundaries.

    For each rendered line:
    - Use Line.value (string) and split into "words" using _split_words.
    - Columns are sized by the widest word in each column.
    - Only existing words are padded, then rejoined.

    Alignment is applied per consecutive group of lines that share the
    same indentation level.
    """

    # Match either:
    #  - double quoted string with possible escapes
    #  - single quoted string with possible escapes
    #  - any other run of non-whitespace characters
    _WORD_PATTERN = re.compile(
        r"""
        "[^"\\]*(?:\\.[^"\\]*)*"     # double-quoted string
    | '[^'\\]*(?:\\.[^'\\]*)*'     # single-quoted string
    | [^\s]+                       # other non-whitespace
        """,
        re.VERBOSE
    )

    def __init__(
        self,
        *children: TChild,
        margin: "Node" = NULL_NODE,
        limit: Optional[int] = None,
    ):
        super().__init__(*children, margin=margin)
        self._limit: Optional[int] = limit

    @property
    def limit(self) -> Optional[int]:
        return self._limit

    @classmethod
    def _split_words(cls,text: str) -> List[str]:
        """
        Split a line into "words" while:

        - Keeping quoted strings (single or double) as a single word.
        - Keeping trailing punctuation such as ',', ')', ']' attached
          to the preceding word.
        - Ignoring differences in internal whitespace, since alignment
          will reformat spacing anyway.
        """
        if not text:
            return []

        raw_tokens = cls._WORD_PATTERN.findall(text)

        if not raw_tokens:
            return []

        # Attach punctuation to the previous token where appropriate
        sticky_punct = {",", ")", "]", "}", ";", ":", ".", "?", "!"}

        merged: List[str] = [raw_tokens[0]]
        for tok in raw_tokens[1:]:
            if tok in sticky_punct and merged:
                merged[-1] = merged[-1] + tok
            else:
                merged.append(tok)
#        print(f"text={text} merged={merged}")
        return merged

    def _align_group(self, group: List["Line"]) -> Iterable["Line"]:
        if len(group) <= 1:
            # Nothing to align
            yield from group
            return

        rows: List[List[str]] = []
        widths: List[int] = []

        # Pass 1: collect words and compute widths
        for ln in group:
            text = ln.value.rstrip()
            words = self._split_words(text)
            rows.append(words)

            for i, w in enumerate(words):
                if self._limit is not None and i >= self._limit:
                    break
                lw = len(w)
                if i == len(widths):
                    widths.append(lw)
                elif lw > widths[i]:
                    widths[i] = lw

        # Pass 2: pad and rebuild lines
        for ln, words in zip(group, rows):
            cols = min(len(words), len(widths))
            if cols > 1:
                for i in range(cols - 1):
                    w = words[i]
                    pad = widths[i] - len(w)
                    if pad > 0:
                        words[i] = w + (" " * pad)
            new_value = " ".join(words) if words else ""
            yield Line(ln.level, new_value)

    def render(
        self,
        level: int = 0,
    ) -> Iterable["Line"]:
        lines_it = super().render(level)

        group: List["Line"] = []
        current_level: int = 0  # dummy default, only meaningful when group is non empty

        for ln in lines_it:
            if not group:
                # Start new group
                current_level = ln.level
                group.append(ln)
            elif ln.level == current_level:
                group.append(ln)
            else:
                # Flush previous group and start new one
                yield from self._align_group(group)
                group = [ln]
                current_level = ln.level

        # Flush last group
        if group:
            yield from self._align_group(group)
