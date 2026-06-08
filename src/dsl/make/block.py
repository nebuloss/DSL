"""
Makefile block constructs: define, conditionals, and condition chains.

MDefine
───────
    define VAR
    body…
    endef

MCondition / MIf / MIfDef / …
──────────────────────────────
Each condition is a standalone DelimitedNodeBlock: begin keyword + body +
endif.  When used alone they render fine.  When combined in MConditionList
the individual endifs are suppressed and only one shared endif is emitted.

MConditionList — the key transformation
────────────────────────────────────────
MConditionList takes N MCondition objects and merges them into one chain:

    if COND_A          ← first.begin
      body_A
    else ifdef COND_B  ← second.begin transformed by with_else_prefix()
      body_B
    else               ← third.begin (an MElse) transformed → "else"
      body_C
    endif              ← first.end  (only one endif for the whole chain)

iter_without_margin() implements this by:
  1. Yielding first.begin as-is.
  2. Yielding first.inner() (indented body).
  3. For each subsequent condition: yielding cond.begin.with_else_prefix()
     then cond.inner() — the condition's own endif is never yielded.
  4. Yielding first.end (the single shared endif).
"""
from typing import Iterator, cast
from dsl.container import DelimitedNodeBlock, NodeStack, SimpleNodeStack
from dsl.make.core import MElement
from dsl.make.keyword import MELSE_KEYWORD, MENDEF_KEYWORD, MENDIF_KEYWORD, MConditionKeyword, MDefineKeyword, MIfDefKeyword, MIfEqKeyword, MIfKeyword, MIfNDefKeyword, MIfNEqKeyword, MKeyword
from dsl.make.var import MExpr, MString, MVar
from dsl.node import Node, nullNode


def _as_name(value: "MExpr | str") -> MExpr:
    """ifdef/ifndef/if expect a variable name; coerce a bare str to MVar."""
    return MVar.coerce(value) if isinstance(value, str) else value


__all__ = [
    "MDelimitedBlock", "MDefine", "MCondition",
    "MIf", "MIfDef", "MIfNDef", "MIfEq", "MIfNEq", "MElse", "MConditionList",
]

class MDelimitedBlock[TBlockHeader:MKeyword](DelimitedNodeBlock[MElement,TBlockHeader,MKeyword]):
    def __init__(self, begin:TBlockHeader, end:MKeyword, *children:MElement,indent:bool=True):
        # Blocks render tight (no blank lines between header, body, footer);
        # spacing between blocks is handled by the enclosing Makefile margin.
        super().__init__(
            begin,
            end,
            *children,
            margin=nullNode,
            level=int(indent)
        )

class MDefine(MDelimitedBlock[MDefineKeyword]):
    def __init__(self, name:MVar , *children):
        super().__init__(
            MDefineKeyword(name),
            MENDEF_KEYWORD,
            *children,
            indent=False
        )

class MCondition(MDelimitedBlock[MConditionKeyword]):
    def __init__(self, begin: MConditionKeyword, *children:MElement):
        super().__init__(begin, MENDIF_KEYWORD, *children,indent=False)

class MIf(MCondition):
    def __init__(self, var: MVar | str, *body: MElement):
        super().__init__(
            MIfKeyword(_as_name(var)),
            *body
        )

class MIfDef(MCondition):
    def __init__(self, var: MVar | str, *body: MElement):
        super().__init__(
            MIfDefKeyword(_as_name(var)),
            *body
        )

class MIfNDef(MCondition):
    def __init__(self, var: MVar | str, *body: MElement):
        super().__init__(
            MIfNDefKeyword(_as_name(var)),
            *body
        )

class MIfEq(MCondition):
    def __init__(self, a:MExpr | str, b:MExpr | str, *body: MElement):
        super().__init__(
        MIfEqKeyword(MString.coerce(a), MString.coerce(b)),
        *body
    )


class MIfNEq(MCondition):
    def __init__(self, a:MExpr | str, b:MExpr | str, *body: MElement):
        super().__init__(
        MIfNEqKeyword(MString.coerce(a), MString.coerce(b)),
        *body
    )


class MElse(MCondition):
    def __init__(self, *children):
        super().__init__(MELSE_KEYWORD, *children)


class MConditionList(NodeStack[MCondition]):
    def __init__(self, *children):
        # Tight chain: if / else if / else / endif with no blank lines between.
        super().__init__(*children, margin=nullNode)

    def iter_without_margin(self)->Iterator[Node]:
        it=cast(Iterator[MCondition],SimpleNodeStack.__iter__(self))
        first=next(it,None)

        if first is None:
            return
        
        yield first.begin
        yield from first.inner()

        for cond in it:
            yield cond.begin.with_else_prefix()
            yield from cond.inner()

        yield first.end

    def __iter__(self):
        yield from self.iter_with_margin(*self.iter_without_margin())
