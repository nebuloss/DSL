from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar, Literal, Optional, Tuple, Union

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


class KConst(VarConst[KconfigOps], ABC):
    """
    Abstract base Kconfig constant.

    Subclasses (KConstBool, KConstInt, KConstString, KConstHex) perform
    validation and normalisation. This class should not be instantiated
    directly.
    """


class KConstBool(KConst):

    def __init__(self, val: Union[str, bool, int]):
        if isinstance(val, bool):
            v = val
        elif isinstance(val, int):
            v = bool(val)
        elif isinstance(val, str):
            s = val.strip().lower()
            if s == "y":
                v = True
            elif s == "n":
                v = False
            else:
                raise TypeError("Bool constant string must be 'y' or 'n'")
        else:
            raise TypeError("Bool constant must be bool, int, or 'y'/'n'")
        super().__init__(v)

    def __str__(self) -> str:
        return "y" if bool(self.val) else "n"
    
    @classmethod
    def true(cls) -> "KConstBool":
        return KConstBool(True)

    @classmethod
    def false(cls) -> "KConstBool":
        return KConstBool(False)


class KConstInt(KConst):

    def __init__(self, val: Union[int, str, bool]):
        if isinstance(val, bool):
            v = int(val)
        elif isinstance(val, int):
            v = val
        elif isinstance(val, str):
            s = val.strip()
            if not s or not s.isdigit():
                raise TypeError("Int constant string must be a decimal integer")
            v = int(s)
        else:
            raise TypeError("Int constant must be int, bool, or decimal string")
        super().__init__(v)

    def __str__(self) -> str:
        return str(int(self.val))


class KConstString(KConst):

    def __init__(self, val: Any):
        super().__init__(str(val))

    @staticmethod
    def _escape_string(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def __str__(self) -> str:
        return f"\"{self._escape_string(str(self.val))}\""


class KConstHex(KConst):

    def __init__(self, val: Union[int, str, bool]):
        if isinstance(val, bool):
            v = int(val)
        elif isinstance(val, int):
            v = val
        elif isinstance(val, str):
            s = val.strip()
            try:
                v = int(s, 16)
            except ValueError:
                raise TypeError("Hex constant string must be a valid hex literal")
        else:
            raise TypeError("Hex constant must be int, bool, or hex string")
        super().__init__(v)

    def __str__(self) -> str:
        return f"0x{int(self.val):X}"


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
KconfigOps.Name = KVar
KconfigOps.Not = KNot
KconfigOps.And = KAnd
KconfigOps.Or = KOr
# KconfigOps.Add/Sub/Mul/Div remain None (no arithmetic)
