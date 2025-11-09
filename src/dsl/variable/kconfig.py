from __future__ import annotations

from typing import Iterable

from dsl.core.var import (
    LanguageOps,
    VarExpr,
    VarConst,
    VarName,
    VarNot,
    VarAnd,
    VarOr,
)


class KconfigOps(LanguageOps):
    """
    LanguageOps table for Kconfig.
    Fields (Const, Name, Not, And, Or) are assigned after class definitions.
    """
    pass


# ---------- Concrete Kconfig nodes ----------

class KConst(VarConst[KconfigOps]):
    def __str__(self) -> str:
        return "y" if self.val else "n"


class KVar(VarName[KconfigOps]):
    @staticmethod
    def normalize(name: str) -> str:
        # Generic normalization, then uppercase for Kconfig style.
        base = VarName.normalize(name)
        return base.upper()

    def __str__(self) -> str:
        return self.name


class KNot(VarNot[KconfigOps]):
    def __str__(self) -> str:
        c = self.child
        if isinstance(c, (KAnd, KOr)):
            return f"!({c})"
        return f"!{c}"


class KAnd(VarAnd[KconfigOps]):
    def __str__(self) -> str:
        l = self.left
        r = self.right

        if isinstance(l, KOr):
            ls = f"({l})"
        else:
            ls = str(l)

        if isinstance(r, KOr):
            rs = f"({r})"
        else:
            rs = str(r)

        return f"{ls} && {rs}"


class KOr(VarOr[KconfigOps]):
    def __str__(self) -> str:
        return f"{self.left} || {self.right}"


# ---------- Fill KconfigOps table ----------

KconfigOps.Const = KConst
KconfigOps.Name = KVar
KconfigOps.Not = KNot
KconfigOps.And = KAnd
KconfigOps.Or = KOr


# ---------- Convenience helpers ----------

def const(val: bool) -> KConst:
    return KConst(val)


def var(name: str) -> KVar:
    return KVar(name)


def all_of(vars_: Iterable[KVar]) -> VarExpr[KconfigOps]:
    it = iter(vars_)
    try:
        expr: VarExpr[KconfigOps] = next(it)
    except StopIteration:
        return KConst(True)
    for v in it:
        expr = expr & v
    return expr


def any_of(vars_: Iterable[KVar]) -> VarExpr[KconfigOps]:
    it = iter(vars_)
    try:
        expr: VarExpr[KconfigOps] = next(it)
    except StopIteration:
        return KConst(False)
    for v in it:
        expr = expr | v
    return expr

