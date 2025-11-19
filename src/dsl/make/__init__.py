from .lang import (
    MElement,
    Makefile,
    MList,
    MComment,
    MCommand,
    MShellCommand,
    MRule,
    MPhony,
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
    MDefine,
    MCondition,
    MIf as MIfBlock,
    MIfDef,
    MIfNDef,
    MIfEq,
    MIfNEq,
    MElse,
    MConditionList,
    MInclude,
)

__all__ = [
    # lang
    "MElement",
    "Makefile",
    "MList",
    "MComment",
    "MCommand",
    "MShellCommand",
    "MRule",
    "MPhony",
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
    "MDefine",
    "MCondition",
    "MIfBlock",
    "MIfDef",
    "MIfNDef",
    "MIfEq",
    "MIfNEq",
    "MElse",
    "MConditionList",
    "MInclude",
]
