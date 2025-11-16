from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .var import (
    KConst as Const,          # abstract base const class
    KConstBool,
    KConstInt,
    KConstHex,
    KConstString,
    KVar,
    KExpr as Expr,
)

from .lang import (
    KElement as Element,
    KConfig as Config,
    KComment as Comment,
    KChoice,
    KBool,
    KInt,
    KHex,
    KMenuconfig,
    KString,
    KMenu,
    KList as List,
    KIf,
    KSource,
)


# ============================================================
# Namespaces: const and option
# ============================================================

@dataclass(frozen=True)
class ConstNS:
    """
    Namespace for typed Kconfig constants.

    Usage:
        k.const.bool(True)
        k.const.int("42")
        k.const.hex("0xFF")
        k.const.string("hello")
        k.const.true
        k.const.false
    """

    bool: type[KConstBool] = KConstBool
    int: type[KConstInt] = KConstInt
    hex: type[KConstHex] = KConstHex
    string: type[KConstString] = KConstString

    @property
    def true(self) -> KConstBool:
        return KConstBool(True)

    @property
    def false(self) -> KConstBool:
        return KConstBool(False)


@dataclass(frozen=True)
class OptionNS:
    """
    Namespace for Kconfig option nodes.

    Usage:
        k.option.bool("DEBUG", prompt="Enable debug", default=k.const.true)
        k.option.int("TIMEOUT", prompt="Timeout", default=k.const.int(100))
        k.option.hex("ADDR", default=k.const.hex("0xFF"))
        k.option.string("NAME", default=k.const.string("foo"))
    """

    bool: type[KBool] = KBool
    int: type[KInt] = KInt
    hex: type[KHex] = KHex
    string: type[KString] = KString
    menu: type[KMenuconfig] = KMenuconfig


const = ConstNS()
option = OptionNS()


# ============================================================
# Expression helpers
# ============================================================

Var = KVar

# Global convenience bool consts
true = KConstBool.true()
false = KConstBool.false()


def var(name: str) -> Var:
    return Var(name)


def all(*vars: Var) -> Expr:
    result: Expr = true
    for v in vars:
        result &= v
    return result


def any(*vars: Var) -> Expr:
    result: Expr = false
    for v in vars:
        result |= v
    return result


# ============================================================
# Structural helpers via simple aliases
# ============================================================

choice = KChoice     # k.choice(...)
menu = KMenu         # k.menu(...)
cond = KIf           # k.cond(expr, ...)

list = List          # k.list(...)
comment = Comment    # k.comment(...)

source = KSource     # k.source("Kconfig.arch")


__all__ = [
    # namespaces
    "const",
    "option",

    # expr types and helpers
    "Const",
    "Var",
    "Expr",
    "true",
    "false",
    "var",
    "all",
    "any",

    # structural builders
    "choice",
    "menu",
    "cond",
    "source",

    # aliases for core node types
    "list",
    "comment",

    # AST nodes if someone wants them directly
    "Element",
    "Config"
]
