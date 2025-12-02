from abc import abstractmethod
from copy import copy
from typing import Iterable, Iterator, List, Self
from dsl.node import Line, Node, NULL_NODE

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
        print(f"{repr(self)} contains {list(iter(self))}")
        for child in self:
            yield from child.render(level)

    def find(self, *tags)-> Iterator[Node]:
#        print(f"{repr(self)} contains {list(iter(self))}")
        yield from super().find(*tags)
        for child in self:
            yield from child.find(*tags)

class IndentedNode[TChild:Node](ContainerNode):
    def __init__(self,child:TChild, level=1):
        self._level=level
        self._child=child
        super().__init__()

    @property
    def level(self)->int:
        return self._level

    @property
    def child(self)->TChild:
        return self._child

    def __iter__(self)-> Iterator["TChild"]:
        yield self.child

    def render(self, level:int = 0):
        yield from self.child.render(level+self.level)

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

    def inner(self) -> Iterator[Node]:
        yield from SimpleNodeStack.__iter__(self)
    
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
        yield from self.iter_with_margin(*self.inner())

class NodeBlock[TChild:Node,TBegin: Node](NodeStack[TChild]):

    def __init__(
        self,
        begin: TBegin,
        *children: TChild,
        margin:Node=NULL_NODE,
        level:int=1
    ):
        # Type-check begin / end according to TBegin / TEnd
        self._begin: TBegin = begin
        self._level=level
        
        super().__init__(*children, margin=margin)

    @property
    def begin(self) -> TBegin:
        return self._begin

    def inner(self) -> Iterator[Node]:
        for node in super().inner():
            yield IndentedNode(node,self._level)

    def __iter__(self) -> Iterable[Node]:
        yield from self.iter_with_margin(self.begin,*self.inner())


class DelimitedNodeBlock[TChild:Node,TBegin: Node, TEnd:Node](NodeBlock[TChild,TBegin]):
    def __init__(
            self, 
            begin: TBegin,
            end: TEnd, 
            *children: TChild, 
            margin = NULL_NODE,
            level:int=1):
        
        super().__init__(begin, *children, margin=margin,level=level)
        self._end: TEnd = end       # type: ignore[assignment]

    @property
    def end(self)->TEnd:
        return self._end
    
    def __iter__(self)->Iterator[Node]:
        yield from self.iter_with_margin(self.begin,*self.inner(),self.end)
