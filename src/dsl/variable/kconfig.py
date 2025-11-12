from __future__ import annotations

from typing import Any, Literal, Union

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

KExpr=VarExpr

from typing import Any, Optional, Tuple

class KConst(VarConst[KconfigOps]):

    SupportedType = Literal["string", "int", "hex", "bool"]

    def __init__(self, val: Any, val_type: Optional["KConst.SupportedType"] = None):
        kind, normalized = self._infer_or_validate(val, val_type)
        self._val_type: "KConst.SupportedType" = kind
        super().__init__(normalized)

    @property
    def val_type(self) -> "KConst.SupportedType":
        return self._val_type

    @staticmethod
    def _infer_or_validate(
        val: Any,
        val_type: Optional["KConst.SupportedType"],
    ) -> Tuple["KConst.SupportedType", Any]:
        if val_type is None:
            match val:
                case bool():
                    return "bool", bool(val)
                case int():
                    return "int", int(val)
                case str():
                    return "string", val
                case _:
                    raise TypeError(f"Unsupported KConst value type: {type(val).__name__}")

        match val_type:
            case "bool":
                match val:
                    case bool():
                        return "bool", val
                    case int():
                        return "bool", bool(val)
                    case str():
                        s = val.strip().lower()
                        if s in ("y", "n"):
                            return "bool", (s == "y")
                        raise TypeError("Bool constant must be bool or 'y'/'n'")
                    case _:
                        raise TypeError("Bool constant must be bool or 'y'/'n'")

            case "string":
               return "string", str(val)

            case "int":
                match val:
                    case bool():
                        return "int", int(val)
                    case int():
                        return "int", val
                    case str():
                        s = val.strip()
                        if s.isdigit():
                            return "int", int(s)
                        raise TypeError("Int constant must be int or decimal str")
                    case _:
                        raise TypeError("Int constant must be int or decimal str")

            case "hex":
                match val:
                    case bool():
                        return "hex", int(val)
                    case int():
                        return "hex", val
                    case str():
                        s = val.strip()
                        try:
                            parsed = int(s, 16)
                        except ValueError:
                            raise TypeError("Hex constant must be int or hex string")
                        return "hex", parsed
                    case _:
                        raise TypeError("Hex constant must be int or hex string")

            case _:
                raise TypeError(f"Unknown SupportedType {val_type!r}")

    @staticmethod
    def _escape_string(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def __str__(self) -> str:
        match self._val_type:
            case "bool":
                return "y" if bool(self.val) else "n"
            case "string":
                return f"\"{self._escape_string(str(self.val))}\""
            case "int":
                return str(int(self.val))
            case "hex":
                return f"0x{int(self.val):X}"
            case _:
                return str(self.val)

    @classmethod
    def true(cls) -> "KConst":
        return cls(True, "bool")

    @classmethod
    def false(cls) -> "KConst":
        return cls(False, "bool")
    
    @classmethod
    def bool(cls,val:Union[str,bool,int]) -> "KConst":
        return cls(val,"bool")
    
    @classmethod
    def int(cls,val:Union[int,str,bool])-> "KConst":
        return cls(val,"int")
    
    @classmethod
    def string(cls, val) -> "KConst":
        return cls(val,"string")
    
    @classmethod
    def hex(cls,val:Union[int,str,bool])-> "KConst":
        return cls(val,"hex")

class KVar(VarName[KconfigOps]):
    @staticmethod
    def normalize(name: str) -> str:
        # Generic normalization, then uppercase for Kconfig style.
        base = super().normalize(name)
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

def const(val: Any) -> KConst:
    return KConst(val)

def var(name: str) -> KVar:
    return KVar(name)

def true() -> KConst:
    return KConst.true()

def false() -> KConst:
    return KConst.false()

def all(*vars:KVar) -> VarExpr[KconfigOps]:
    result=KConst.true()
    for var in vars:
        result&=var
    return result

def any(*vars:KVar) -> VarExpr[KconfigOps]:
    result=KConst.false()
    for var in vars:
        result|=var
    return result

def kbool(v: Union[bool, str]) -> KConst:
    return KConst.bool(v)

def kstr(s: str) -> KConst:
    return KConst.string(s)

def kint(n: int) -> KConst:
    return KConst.int(n)

def khex(v: Union[int, str]) -> KConst:
    return KConst.hex(v)
