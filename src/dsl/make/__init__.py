from .core import (
    MElement,
    Makefile,
    MList,
    MComment,
    MCommand,
    MText,
    MLine,
)

from .var import (
    MExpr,
    MNull,
    mNULL,
    MVar,
    MBool,
    MString,
    MArg,
    MAdd,
    MAnd,
    MOr,
    MNot,
    mTargetVar,
    mFirstPrerequisiteVar,
    mPrerequisitesVar
)

from .rule import (
    MRule,
    MStaticRule,
    MIndependantRule,
    MGroupedRule,
    MReceipe,
    MPhony
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

def any(*exprs:MExpr)->MExpr:
    result=MBool.false()
    for var in exprs:
        result|=var
    return result

def all(*exprs:MExpr)->MExpr:
    result=MBool.true()
    for var in exprs:
        result&=var
    return result

__all__ = [
    # lang
    "MElement",
    "Makefile",
    "MList",
    "MComment",
    "MCommand",
    "MText",
    "MLine",

    # var
    "MLanguage",
    "MExpr",
    "MNull",
    "MVar",
    "MArg",
    "MAdd",
    "MAnd",
    "MOr",
    "MNot",
    # const
    "MBool",
    "MString",
    "mNULL",
    "mTargetVar",
    "mFirstPrerequisiteVar",
    "mPrerequisitesVar",

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
    "MStaticRule",
    "MIndependantRule",
    "MGroupedRule",
    "MReceipe",
    "MPhony",

    #functions
    "all",
    "any"
]
