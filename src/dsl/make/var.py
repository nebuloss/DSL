from __future__ import annotations

from typing import Any, List

from dsl.var import (
    Language,
    Language,
    VarAdd,
    VarAnd, 
    VarBool, 
    VarExpr, 
    VarName,
    VarNot, 
    VarNull,
    VarOr, 
    VarString
)


make=Language("make")

# ---------- Core Makefile expression types ----------

MExpr = VarExpr

class MNull(VarNull[make]):
    def __str__(self):
        return ""
    
class MBool(VarBool[make]):
    def __str__(self):
        if self.value:
            return "1"
        
        return ""
    
class MString(VarString[make]):
    def __str__(self):
        return self.value
       

class MVarName(VarName[make]):
    pass

class MVar(MVarName):
    def __init__(self, name):
        super().__init__(name, special_chars="-.")

    def __str__(self) -> str:
        return f"$({self.name})"
        
class MArg(MVar):
    def __init__(self, n:int):
        if not isinstance(n,int):
            raise TypeError(f"Expected int got {type(n).__name__}")
        super().__init__(str(n))

class MSpecialVar(MVarName):
    def __init__(self, name):
        if len(name)!=1:
            raise ValueError("special variable in makefile have a one character length")
        super().__init__(name, special_chars="@<^")

    def __str__(self):
        return "$"+self.name

class MAdd(VarAdd[make]):
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

    def __str__(self) -> str:
        return self._join(self.left, self.right)


class MAnd(VarAnd[make]):
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


class MOr(VarOr[make]):
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

class MNot(VarNot[make]):
    def __str__(self) -> str:
        return f"$(if {self.child},,1)"


mNULL=MNull()
mTargetVar=MSpecialVar("@")
mFirstPrerequisiteVar=MSpecialVar("<")
mPrerequisitesVar=MSpecialVar("^")
# Make.Sub/Mul/Div remain None
