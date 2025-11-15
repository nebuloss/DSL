from .var import (
    KConst as Const,
    KVar as Var,
    KExpr as Expr,
)

from .lang import (
    KElement as Element,
    KConfig as Config,
    KComment as Comment,
    KChoice as Choice,
    KBool as Bool,
    KInt as Int,
    KHex as Hex,
    KString as String,
    KMenu as Menu,
    KList as List,
    KIf as If,
    KSource as Source,
    KMenuconfig as MenuConfig
)

# Convenience constants
true = Const.true()
false = Const.false()


def all(*vars: Var) -> Expr:
    """
    Logical AND over a sequence of Var.
    all(a, b, c) becomes a & b & c, starting from true.
    """
    result: Expr = true
    for var in vars:
        result &= var
    return result


def any(*vars: Var) -> Expr:
    """
    Logical OR over a sequence of Var.
    any(a, b, c) becomes a | b | c, starting from false.
    """
    result: Expr = false
    for var in vars:
        result |= var
    return result


__all__ = [
    # expression types and helpers
    "Const",
    "Var",
    "Expr",
    "true",
    "false",
    "all",
    "any",

    # AST node aliases
    "Element",
    "Config",
    "Comment",
    "Choice",
    "Bool",
    "Int",
    "Hex",
    "String",
    "Menu",
    "List",
    "If",
    "Source",
    "MenuConfig"
]
