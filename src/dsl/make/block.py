from typing import Generic, TypeVar
from dsl.container import DelimitedNodeBlock
from dsl.make.core import MElement, Makefile
from dsl.make.keyword import MConditionKeyword, MDefineKeyword, MEndefKeyword, MEndifKeyword, MKeyword, MSingleKeyword
from dsl.make.var import MExpr, MVar

TBlockHeader = TypeVar("TChildHeader", bound=MKeyword)

class MBlock(DelimitedNodeBlock[MElement,TBlockHeader,MSingleKeyword],Generic[TBlockHeader]):
    def __init__(self, begin:TBlockHeader, end:MSingleKeyword, *children:MElement):
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
            MEndefKeyword,
            *children
        )

class MCondition(MBlock[MConditionKeyword]):
    def __init__(self, begin: MConditionKeyword, *children:MElement):
        super().__init__(begin, MEndifKeyword, *children)

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


class MConditionList(SimpleNodeStack[MCondition]):
    def __iter__(self):
        for i,child in enumerate(SimpleNodeStack.__iter__(self)):
            yield child.generate_condition_statement(else_keyword=bool(i))
            yield child.inner()
        yield MCondition.ENDIF

class MInclude(TextNode):
    """
    Makefile include line.

    - Escapes spaces in each path (foo bar -> foo\\ bar)
    - Supports multiple paths:
        MInclude("a.mk", "b mk") -> include a.mk b\\ mk
    """
    @staticmethod
    def _escape_spaces(path: str) -> str:
        """Escape spaces for use in a Makefile include."""
        # Make treats backslash-space as a single space character in the filename.
        return path.replace(" ", r"\ ")

    def __init__(self, *paths: str):
        if not paths:
            raise ValueError("MInclude requires at least one path")

        parts: list[str] = []

        for p in paths:
            if not isinstance(p, str):
                raise TypeError("include paths must be strings")
            
            p = self._escape_spaces(p)
            parts.append(p)

        line = "include " + " ".join(parts)
        super().__init__(line)
