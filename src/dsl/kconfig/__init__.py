from .core import (
    KConfig,
    KElement,
    KList,
    KSource,
    KComment,
)

from .var import (
    KLanguage,
    KVar,
    KExpr,
    KExpr,
    KNot,
    KAnd,
    KOr,
    KBool,
    KInt,
    KString,
    KHex,
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
    result=KBool.false()
    for var in exprs:
        result|=var
    return result

def all(*exprs:KExpr)->KExpr:
    result=KBool.true()
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
    "KLanguage",
    "KExpr",
    "KVar",
    "KConst",
    "KExpr",
    "KNot",
    "KAnd",
    "KOr",

    # const
    "KBool",
    "KInt",
    "KString",
    "KHex",

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
