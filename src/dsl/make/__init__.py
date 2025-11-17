from .lang import (
    MElement,
    Makefile,
    MList,
    Comment,
    Command,
    ShellCommand,
    Rule,
    Phony,
    Line,
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
    MFunction,
    MIf,
    MEval,
    MShell,
    MCall,
    MForeach,
)

from .keyword import (
    MDefine,
    MIfExpr,
    MIf as MIfBlock,
    MIfDef,
    MIfNDef,
    MIfEq,
    MIfNEq,
    MElse,
    MIfList,
    MInclude,
)

__all__ = [
    # lang
    "MElement",
    "Makefile",
    "MList",
    "Comment",
    "Command",
    "ShellCommand",
    "Rule",
    "Phony",
    "Line",

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
    "MFunction",
    "MIf",
    "MEval",
    "MShell",
    "MCall",
    "MForeach",

    # keyword
    "MDefine",
    "MIfExpr",
    "MIfBlock",
    "MIfDef",
    "MIfNDef",
    "MIfEq",
    "MIfNEq",
    "MElse",
    "MIfList",
    "MInclude",
]
