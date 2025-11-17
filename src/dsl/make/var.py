from __future__ import annotations

from typing import Any, List

from dsl import (
    LanguageOps,
    VarExpr,
    VarConst,
    VarName,
    VarNot,
    VarAnd,
    VarNull,
    VarOr,
    VarAdd,
)


class MakeOps(LanguageOps):
    """LanguageOps table for Makefile-like expressions."""
    pass


# ---------- Core Makefile expression types ----------

MExpr = VarExpr

class MNull(VarNull[MakeOps]):
    def __str__(self):
        return ""

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
    def __str__(self) -> str:
        return f"$({self.name})"
    
class MArg(MVar):
    def __init__(self, n:int):
        super().__init__(str(n))

class MAdd(VarAdd[MakeOps]):
    """
    Concatenation for Make expressions: expr + expr.

    Semantics:
      - Children are simplified first.
      - If both sides are MConst, they are merged into a single MConst.
      - Otherwise, printing concatenates the two sides with a single space
        between them (when both sides are non-empty).
    """

    @staticmethod
    def _join(a: Any, b: Any) -> str:
        ls = str(a).strip()
        rs = str(b).strip()
        if not ls:
            return rs
        if not rs:
            return ls
        return f"{ls} {rs}"

    def simplify(self) -> MExpr:
        left = self.left
        right = self.right

        if isinstance(left, MConst) and isinstance(right, MConst):
            return MConst(self._join(left, right))

        return MAdd(left, right)

    def __str__(self) -> str:
        return self._join(self.left, self.right)


class MAnd(VarAnd[MakeOps]):
    def __str__(self) -> str:
        # Flatten nested ANDs so we can emit a single $(and a,b,c)
        terms: List[str] = []

        def walk(e: MExpr) -> None:
            if isinstance(e, MAnd):
                walk(e.left)
                walk(e.right)
            else:
                terms.append(str(e))

        walk(self.left)
        walk(self.right)

        if len(terms) == 1:
            return terms[0]
        return f"$(and {','.join(terms)})"


class MOr(VarOr[MakeOps]):
    def __str__(self) -> str:
        # Flatten nested ORs so we can emit a single $(or a,b,c)
        terms: List[str] = []

        def walk(e: MExpr) -> None:
            if isinstance(e, MOr):
                walk(e.left)
                walk(e.right)
            else:
                terms.append(str(e))

        walk(self.left)
        walk(self.right)

        if len(terms) == 1:
            return terms[0]
        return f"$(or {','.join(terms)})"

class MNot(VarNot[MakeOps]):
    def __str__(self) -> str:
        return f"$(if {self.child},,1)"

# ---------- Fill MakeOps table ----------

MakeOps.Const = MConst
MakeOps.Name = MVar
MakeOps.Not = MNot
MakeOps.And = MAnd
MakeOps.Or = MOr
MakeOps.Add = MAdd
MakeOps.Null= MNull
# MakeOps.Sub/Mul/Div remain None
