from .core import (
    KConfig,
    KElement,
    KList,
    KSource,
    KComment,
)

from .var import (
    KVar,
    KExpr,
    KNot,
    KAnd,
    KOr,
    KNull,
    kNULL,
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

def any_of(*exprs: KExpr) -> KExpr:
    result = KBool.false()
    for var in exprs:
        result |= var
    return result

def all_of(*exprs: KExpr) -> KExpr:
    result = KBool.true()
    for var in exprs:
        result &= var
    return result

__all__ = [
    # lang
    "KConfig",
    "KElement",
    "KList",
    "KSource",
    "KComment",

    # var
    "KExpr",
    "KVar",
    "KNull",
    "kNULL",
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

    # functions
    "all_of",
    "any_of",
]
