from __future__ import annotations


from dsl import (
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
    Optional Add/Sub/Mul/Div are unused for Kconfig.
    """
    pass


# ---------- Concrete Kconfig nodes ----------

KExpr = VarExpr

class KConst(VarConst[KconfigOps]):
    """
    Abstract base Kconfig constant.

    Subclasses (KConstBool, KConstInt, KConstString, KConstHex) perform
    validation and normalisation. This class should not be instantiated
    directly.
    """

    @classmethod
    def typename(cls) -> str:
        return "generic"
    
    def __str__(self):
        return "y" if bool(self.val) else "n"

class KVar(VarName[KconfigOps]):
    @staticmethod
    def normalize(name: str) -> str:
        # Use VarName normalization, then uppercase for Kconfig style
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
KconfigOps.Name = KExpr
KconfigOps.Not = KNot
KconfigOps.And = KAnd
KconfigOps.Or = KOr
# KconfigOps.Add/Sub/Mul/Div remain None (no arithmetic)
