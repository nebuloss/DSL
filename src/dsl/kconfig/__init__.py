from .core import (
    KConfig,
    KElement,
    KList,
    KStringKey,
    KSource,
    KComment,
)

from .var import (
    KconfigOps,
    KVar,
    KExpr,
    KConst,
    KExpr,
    KNot,
    KAnd,
    KOr,
)

from .const import (
    KConstBool,
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

def any(*vars:KVar)->KExpr:
    result=KConst.false()
    for var in vars:
        result|=var
    return result

def all(*vars:KVar)->KExpr:
    result=KConst.true()
    for var in vars:
        result&=var
    return result

__all__ = [
    # lang
    "KConfig",
    "KElement",
    "KList",
    "KStringKey",
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
    "KConstBool",
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
