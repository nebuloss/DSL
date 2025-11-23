from typing import Generic, Iterator, TypeVar
from dsl.container import DelimitedNodeBlock, NodeStack, SimpleNodeStack
from dsl.make.core import MElement, Makefile
from dsl.make.keyword import MELSE_KEYWORD, MENDEF_KEYWORD, MENDIF_KEYWORD, MConditionKeyword, MDefineKeyword, MIfDefKeyword, MIfEqKeyword, MIfKeyword, MIfNDefKeyword, MIfNEqKeyword, MKeyword
from dsl.make.var import MExpr, MVar
from dsl.node import Node

TBlockHeader = TypeVar("TBlockHeader", bound=MKeyword)

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
            MENDEF_KEYWORD,
            *children
        )

class MCondition(MBlock[MConditionKeyword]):
    def __init__(self, begin: MConditionKeyword, *children:MElement):
        super().__init__(begin, MENDIF_KEYWORD, *children)

class MIf(MCondition):
    def __init__(self, var: MVar, *body: MElement):
        super().__init__(
            MIfKeyword(var),
            *body
        )

class MIfDef(MCondition):
    def __init__(self, var: MVar, *body: MElement):
        super().__init__(
            MIfDefKeyword(var),
            *body
        )

class MIfNDef(MCondition):
    def __init__(self, var: MVar, *body: MElement):
        super().__init__(
            MIfNDefKeyword(var),
            *body
        )

class MIfEq(MCondition):
    def __init__(self, a:MExpr, b:MExpr, *body: MElement):
        super().__init__(
        MIfEqKeyword(a,b),
        *body
    )


class MIfNEq(MCondition):
    def __init__(self, a:MExpr, b:MExpr, *body: MElement):
        super().__init__(
        MIfNEqKeyword(a,b),
        *body
    )


class MElse(MCondition):
    def __init__(self, *children):
        super().__init__(MELSE_KEYWORD, *children)


class MConditionList(NodeStack[MCondition]):
    def __init__(self, *children):
        super().__init__(*children, margin=Makefile.MARGIN)

    def iter_without_margin(self)->Iterator[Node]:
        it=SimpleNodeStack.__iter__(self)
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
