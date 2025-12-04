from typing import Iterable, Iterator
from dsl.node import IterableNode, LevelNode, Line, ListNode, Node, nullNode

class ContainerNode[TChild:Node](IterableNode[TChild]):
    """
    Base class for containers of child nodes with a single child type.

    - __class_getitem__ makes ContainerNode[T] (and subclasses) real subclasses
      whose __orig_bases__ contain GenericAlias(cls, (T,)).
    - child_type is resolved once in __init__ via resolve_generic_type_arg.
    - ensure_type / ensure_child_type centralise runtime checks.
    """

    def empty(self) -> bool:
        return next(iter(self), None) is None
    
    def render(self, level: int = 0) -> Iterator[Line]:
#        print(f"{repr(self)} contains {list(iter(self))}")
        for child in self:
            yield from child.render(level)

    def find(self, *tags)-> Iterator[Node]:
#        print(f"{repr(self)} contains {list(iter(self))}")
        yield from super().find(*tags)
        for child in self:
            yield from child.find(*tags)

class SingleContainerNode[TChild:Node](ContainerNode[TChild]):
    def __init__(self,child:TChild):
        ContainerNode.__init__(self)
        self._child=child
    
    @property
    def child(self)->TChild:
        return self._child
    
    def __iter__(self)-> Iterator[TChild]:
        yield self.child

class IndentedNode[TChild:Node](SingleContainerNode[TChild],LevelNode):
    def __init__(self,child:TChild, level=1):
        SingleContainerNode.__init__(self,child)
        LevelNode.__init__(self,level)

    def render(self, level:int = 0):
        yield from self.child.render(level+self.level)

class FixedNode[TChild:Node](SingleContainerNode[TChild],LevelNode):
    def __init__(self,child:TChild, level=0):
        SingleContainerNode.__init__(self,child)
        LevelNode.__init__(self,level)

    def render(self, level:int = 0):
        yield from self.child.render(self.level)
    
class SimpleNodeStack[TChild: Node](ListNode[TChild],ContainerNode[TChild]):
    pass

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
        margin: Node = nullNode,
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
        margin:Node=nullNode,
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
            margin = nullNode,
            level:int=1):
        
        super().__init__(begin, *children, margin=margin,level=level)
        self._end: TEnd = end       # type: ignore[assignment]

    @property
    def end(self)->TEnd:
        return self._end
    
    def __iter__(self)->Iterator[Node]:
        yield from self.iter_with_margin(self.begin,*self.inner(),self.end)
