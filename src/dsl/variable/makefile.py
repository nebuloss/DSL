# =========================
# Makefile language binding
# =========================

import re
from typing import Any

from dsl.core.var import (
    LanguageOps,
    VarExpr,
    VarConst,
    VarName,
    VarNot,
    VarAnd,
    VarOr,
)

class MakeOps(LanguageOps):
    """LanguageOps table for Makefile-like expressions."""
    pass


# ---------- Concrete Makefile nodes ----------

class MConst(VarConst[MakeOps]):
    def __str__(self) -> str:
        # Booleans: True -> "1", False -> ""
        if self.val is True:
            return "1"
        if self.val is False:
            return ""
        # Any other constant prints as-is (non-empty strings are truthy in $(if ...))
        return str(self.val)


class MVar(VarName[MakeOps]):
    @staticmethod
    def normalize(name: str) -> str:
        # Replace spaces, tabs, hyphens with _, then validate identifier
        s = name.strip()
        if not s:
            raise ValueError("Empty variable name")
        s = re.sub(r"[ \t-]+", "_", s)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s):
            raise ValueError(f"Illegal variable name: {name!r}")
        return s

    def __str__(self) -> str:
        return f"$({self.name})"


class MNot(VarNot[MakeOps]):
    def __str__(self) -> str:
        # NOT is rendered as $(if <expr>,,1)
        # If child is binary, its own __str__ yields the function call already
        return f"$(if {self.child},,1)"


class MAnd(VarAnd[MakeOps]):
    def __str__(self) -> str:
        # Flatten nested ANDs so we can emit a single $(and a,b,c)
        terms = []

        def walk(e: VarExpr[MakeOps]) -> None:
            if isinstance(e, MAnd):
                walk(e.left)
                walk(e.right)
            else:
                terms.append(str(e))

        walk(self.left)
        walk(self.right)

        # $(and a) is just a
        if len(terms) == 1:
            return terms[0]
        return f"$(and {",".join(terms)})"


class MOr(VarOr[MakeOps]):
    def __str__(self) -> str:
        # Flatten nested ORs so we can emit a single $(or a,b,c)
        terms = []

        def walk(e: VarExpr[MakeOps]) -> None:
            if isinstance(e, MOr):
                walk(e.left)
                walk(e.right)
            else:
                terms.append(str(e))

        walk(self.left)
        walk(self.right)

        # $(or a) is just a
        if len(terms) == 1:
            return terms[0]
        return f"$(or {",".join(terms)})"


# ---------- Fill MakeOps table ----------

MakeOps.Const = MConst
MakeOps.Name  = MVar
MakeOps.Not   = MNot
MakeOps.And   = MAnd
MakeOps.Or    = MOr


# ---------- Convenience helpers ----------

def const(val: Any) -> MConst:
    return MConst(val)

def true() -> MConst:
    return MConst.true()

def false() -> MConst:
    return MConst.false()

def var(name: str) -> MVar:
    return MVar(name)

def all(*vars: MVar) -> VarExpr[MakeOps]:
    acc: VarExpr[MakeOps] = MConst.true()
    for v in vars:
        acc = acc & v
    return acc

def any(*vars: MVar) -> VarExpr[MakeOps]:
    acc: VarExpr[MakeOps] = MConst.false()
    for v in vars:
        acc = acc | v
    return acc
