"""
Kconfig expression types.

All classes bind to  kconfig = Language("kconfig")  defined here.

Kconfig boolean expressions use C-like operators in the generated output:
  &&  ||  !   (parentheses added around sub-expressions where needed)

KVar normalises names to UPPER_CASE and replaces dots/dashes with underscores,
matching Kconfig's symbol naming convention.

KNull is the identity element for boolean operators; it lets callers write
  cond | kNULL  →  cond   (same as  cond | False  but type-safe)

Type mapping
────────────
  KBool    →  y / n
  KInt     →  decimal integer
  KHex     →  0xHEX  (stored as int, displayed as hex)
  KString  →  "quoted string"  (backslash and quote are escaped)

Note: KHex extends VarHex[kconfig] — NOT KInt — so that it registers as
kconfig.types.Hex rather than overwriting kconfig.types.Int.
"""
from __future__ import annotations

from dsl import (
    Language,
    VarExpr,
    VarName,
    VarNot,
    VarAnd,
    VarOr,
)

from dsl.var import LanguageOps, LanguageTypes, VarBool, VarHex, VarInt, VarNull, VarString

kconfig=Language("kconfig")


# ---------- Concrete Kconfig nodes ----------

KExpr = VarExpr

class KVar(VarName[kconfig]):
    def __init__(self, name:str):
        if name[0].isdigit():
            raise ValueError("Variable name cannot start with a digit")
        super().__init__(name.upper().replace(".","_").replace("-", "_"))

    def __str__(self) -> str:
        return self.name


class KNot(VarNot[kconfig]):
    def __str__(self) -> str:
        c = self.child
        if isinstance(c, (KAnd, KOr)):
            return f"!({c})"
        return f"!{c}"


class KAnd(VarAnd[kconfig]):
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


class KOr(VarOr[kconfig]):
    def __str__(self) -> str:
        return f"{self.left} || {self.right}"


from typing import Any, Union


class KNull(VarNull[kconfig]):
    def __str__(self) -> str:
        return ""

kNULL = KNull()


class KBool(VarBool[kconfig]):

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

class KInt(VarInt[kconfig]):

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

class KHex(VarHex[kconfig]):

    def __init__(self, val: Union[int, str, bool]):
        if isinstance(val, str):
            s = val.strip()
            try:
                v = int(s, 16)
            except ValueError:
                raise TypeError("Hex constant string must be a valid hex literal")
            super().__init__(v)
        else:
            super().__init__(val)

    def __str__(self) -> str:
        return f"0x{int(self._val):X}"


class KString(VarString[kconfig]):

    def __init__(self, val: Any):
        super().__init__(str(val))

    @staticmethod
    def _escape_string(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def __str__(self) -> str:
        return f"\"{self._escape_string(str(self._val))}\""
