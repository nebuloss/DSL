from typing import Generic, Iterator, TypeVar
from dsl.container import DelimitedNodeBlock, NodeStack, SimpleNodeStack
from dsl.make.core import MElement, Makefile
from dsl.make.keyword import MConditionKeyword, MDefineKeyword, MKeyword
from dsl.make.var import MExpr, MVar
from dsl.node import Node

TBlockHeader = TypeVar("TChildHeader", bound=MKeyword)

class MBlock(DelimitedNodeBlock[MElement,TBlockHeader,MKeyword],Generic[TBlockHeader]):
    def __init__(self, begin:TBlockHeader, end:MKeyword, *children:MElement):
        super().__init__(
            begin, 
            end, 
            *children, 
            margin=Makefile.MARGIN
        )

class MDefine(MBlock[MDefineKeyword]):
    def __init__(self, name:MVar , *children):
        super().__init__(
            MDefineKeyword(name),
            MKeyword("endef"),
            *children
        )

class MCondition(MBlock[MElement]):
    def __init__(self, begin: MConditionKeyword, *children:MElement):
        super().__init__(begin, MKeyword("endif"), *children)

class MIf(MCondition):
    def __init__(self, var: MVar, *body: MElement):
        super().__init__(
            MConditionKeyword("if",var),
            *body
        )

class MIfDef(MCondition):
    def __init__(self, var: MVar, *body: MElement):
        super().__init__(
            MConditionKeyword("ifdef",var),
            *body
        )

class MIfNDef(MCondition):
    def __init__(self, var: MVar, *body: MElement):
        super().__init__(
            MConditionKeyword("ifndef",var),
            *body
        )

class MIfEq(MCondition):
    def __init__(self, a:MExpr, b:MExpr, *body: MElement):
        super().__init__(
        MConditionKeyword("ifeq",a,b),
        *body
    )


class MIfNEq(MCondition):
    def __init__(self, a:MExpr, b:MExpr, *body: MElement):
        super().__init__(
        MConditionKeyword("ifneq",a,b),
        *body
    )


class MElse(MCondition):
    def __init__(self, *children):
        super().__init__(MConditionKeyword("else"), *children)


class MConditionList(NodeStack[MCondition]):
    def __init__(self, *children):
        super().__init__(*children, margin=Makefile.MARGIN)

    def iter_without_margin(self)->Iterator[Node]:
        it=SimpleNodeStack[MCondition].__iter__(self)
        first=next(it,None)

        if first is None:
            return
        
        yield first.begin
        yield first.inner()

        for cond in it:
            yield cond.begin.with_else_prefix()
            yield cond.inner()

        yield first.end

    def __iter__(self):
        yield from self.iter_with_margin(*self.iter_without_margin())
