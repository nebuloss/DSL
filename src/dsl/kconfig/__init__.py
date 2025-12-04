from .core import (
    KConfig,
    KElement,
    KList,
    KSource,
    KComment,
)

from .var import (
    KconfigOps,
    KVar,
    KExpr,
    KExpr,
    KNot,
    KAnd,
    KOr,
)

from .const import (
    KConst,
    KBool,
    KConstInt,
    KConstString,
    KConstHex,
)

from .option import (
    KOption,
    KOptionBool,
    KOptionString,
    KOptionInt,
    KOptionHex,
    KMenuConfig,
    KChoiceHeader,
)

from .block import (
    KBlock,
    KIf,
    KMenu,
    KChoice,
)

def any(*exprs:KExpr)->KExpr:
    result=KConst.false()
    for var in exprs:
        result|=var
    return result

def all(*exprs:KExpr)->KExpr:
    result=KConst.true()
    for var in exprs:
        result&=var
    return result

__all__ = [
    # lang
    "KConfig",
    "KElement",
    "KList",
    "KSource",
    "KComment",

    # var
    "KconfigOps",
    "KExpr",
    "KVar",
    "KConst",
    "KExpr",
    "KNot",
    "KAnd",
    "KOr",

    # const
    "KBool",
    "KConstInt",
    "KConstString",
    "KConstHex",

    # option
    "KOption",
    "KOptionBool",
    "KOptionString",
    "KOptionInt",
    "KOptionHex",
    "KMenuConfig",
    "KChoiceHeader",

    # block
    "KBlock",
    "KIf",
    "KMenu",
    "KChoice",

    #functions
    "all",
    "any"
]
