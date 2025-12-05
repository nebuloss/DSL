from __future__ import annotations

from dsl import (
    Language,
    VarExpr,
    VarName,
    VarNot,
    VarAnd,
    VarOr,
)

from dsl.var import LanguageOps, LanguageTypes

class KLanguage(Language):
    """
    LanguageOps table for Kconfig.
    Fields (Const, Name, Not, And, Or) are assigned after class definitions.
    Optional Add/Sub/Mul/Div are unused for Kconfig.
    """
    pass


# ---------- Concrete Kconfig nodes ----------

KExpr = VarExpr

class KVar(VarName[KLanguage]):
    def __init__(self, name:str):
        if name[0].isdigit():
            raise ValueError("Variable name cannot start with a digit")
        super().__init__(name.upper().replace(".","_").replace("-", "_"))

    def __str__(self) -> str:
        return self.name


class KNot(VarNot[KLanguage]):
    def __str__(self) -> str:
        c = self.child
        if isinstance(c, (KAnd, KOr)):
            return f"!({c})"
        return f"!{c}"


class KAnd(VarAnd[KLanguage]):
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


class KOr(VarOr[KLanguage]):
    def __str__(self) -> str:
        return f"{self.left} || {self.right}"

from typing import Any, Union

from dsl.kconfig.var import KLanguage
from dsl.var import VarBool, VarInt, VarString

class KBool(VarBool[KLanguage]):

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
        return "y" if self.value else "n"

class KInt(VarInt[KLanguage]):

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
        return str(int(self._val))

class KHex(KInt):
    TYPE="hex"

    def __init__(self, val: Union[int, str, bool]):
        if isinstance(val, str):
            s = val.strip()
            try:
                v = int(s, 16)
            except ValueError:
                raise TypeError("Hex constant string must be a valid hex literal")
        else:
            v=val
        super().__init__(v)

    def __str__(self) -> str:
        return f"0x{int(self._val):X}"
    

class KString(VarString[KLanguage]):

    def __init__(self, val: Any):
        super().__init__(str(val))

    @staticmethod
    def _escape_string(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def __str__(self) -> str:
        return f"\"{self._escape_string(str(self._val))}\""



KLanguage.types= LanguageTypes(
    Name=KVar,
    String=KString,
    Bool=KBool,
    Int=KInt
)

KLanguage.ops= LanguageOps(
    Not=KNot,
    And=KAnd,
    Or=KOr
)
# KconfigOps.Add/Sub/Mul/Div remain None (no arithmetic)
