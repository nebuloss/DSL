from .core import (
    MElement,
    Makefile,
    MList,
    MComment,
    MCommand,
    MShellCommand,
    MLine,
)

from .var import (
    MakeOps,
    MExpr,
    MNull,
    MConst,
    MVar,
    MArg,
    MAdd,
    MAnd,
    MOr,
    MNot,
    MNULL
)

from .rule import (
    MRule,
    MPhonyRule,
    MDefaultRule,
    MAllRule
)

from .assignment import (
    MAssignment,
    MSet,
    MSetImmediate,
    MSetDefault,
    MAppend,
    MAssignmentList,
)

from .function import (
    MFunc,
    MIfFunc,
    MEvalFunc,
    MShellFunc,
    MCallFunc,
    MForeachFunc,
)

from .keyword import (
    MIncludeKeyword as MInclude,
    MDefineKeyword,
    MENDEF_KEYWORD,
    MIfKeyword,
    MIfDefKeyword,
    MIfNDefKeyword,
    MIfEqKeyword,
    MIfNEqKeyword,
    MELSE_KEYWORD,
    MENDIF_KEYWORD
)

from .block import (
    MIf,
    MIfDef,
    MIfNDef,
    MIfEq,
    MIfNEq,
    MElse,
    MConditionList
)

def any(*vars:MVar)->MExpr:
    result=MConst.false()
    for var in vars:
        result|=var
    return result

def all(*vars:MVar)->MExpr:
    result=MConst.true()
    for var in vars:
        result&=var
    return result

__all__ = [
    # lang
    "MElement",
    "Makefile",
    "MList",
    "MComment",
    "MCommand",
    "MShellCommand",
    "MLine",

    # var
    "MakeOps",
    "MExpr",
    "MNull",
    "MConst",
    "MVar",
    "MArg",
    "MAdd",
    "MAnd",
    "MOr",
    "MNot",
    # const
    "MNULL",

    # assignment
    "MAssignment",
    "MSet",
    "MSetImmediate",
    "MSetDefault",
    "MAppend",
    "MAssignmentList",

    # function
    "MFunc",
    "MIfFunc",
    "MEvalFunc",
    "MShellFunc",
    "MCallFunc",
    "MForeachFunc",

    # keyword
    "MInclude",
    "MDefineKeyword",
    "MIfKeyword",
    "MIfDefKeyword",
    "MIfNDefKeyword",
    "MIfEqKeyword",
    "MIfNEqKeyword",
    "MENDEF_KEYWORD",
    "MENDIF_KEYWORD",
    "MELSE_KEYWORD",

    #block
    "MDefine",
    "MCondition",
    "MIf",
    "MIfDef",
    "MIfNDef",
    "MIfEq",
    "MIfNEq",
    "MElse",
    "MConditionList",
    

    #rule
    "MRule",
    "MPhonyRule",
    "MDefaultRule",
    "MAllRule",

    #functions
    "all",
    "any"
]
