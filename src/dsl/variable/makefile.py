from __future__ import annotations

from typing import Any, List, Optional

from dsl.core.variable import (
    LanguageOps,
    VarExpr,
    VarConst,
    VarName,
    VarNot,
    VarAnd,
    VarOr,
    VarAdd,
)


class MakeOps(LanguageOps):
    """LanguageOps table for Makefile-like expressions."""
    pass


# ---------- Core Makefile expression types ----------

MExpr = VarExpr


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
        left = self.left.simplify()
        right = self.right.simplify()

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


# ---------- Shared base for Make "functions" ----------

class MFunc(MExpr):
    """
    Base class for Make function-like expressions:
      $(name arg1,arg2,...)
    """

    def __init__(self, name: str, *args: MExpr):
        super().__init__()
        self._name = name
        self._args: List[MExpr] = list(args)

    @property
    def name(self) -> str:
        return self._name

    @property
    def args(self) -> tuple[MExpr, ...]:
        return tuple(self._args)

    def key(self) -> tuple[Any, ...]:
        return (
            self._name,
            tuple(a.key() for a in self._args),
        )

    def simplify(self) -> MExpr:
        new_args: List[MExpr] = []
        changed = False
        for a in self._args:
            sa = a.simplify()
            if sa is not a:
                changed = True
            new_args.append(sa)

        if changed:
            self._args = new_args
        return self

    def __len__(self) -> int:
        # Simple complexity: 1 for the function node, plus children
        return 1 + sum(len(a) for a in self._args)

    def __str__(self) -> str:
        if not self._args:
            return f"$({self._name})"
        return f"$({self._name} {','.join(str(a) for a in self._args)})"


# ---------- Higher-level Make expressions ----------

class MIf(MFunc):
    """$(if cond,then[,else])"""

    def __init__(
        self,
        cond: MExpr,
        then: Optional[MExpr] = None,
        otherwise: Optional[MExpr] = None,
    ):
        if then is None:
            then = MConst.false()
        args: List[MExpr] = [cond, then]
        if otherwise is not None:
            args.append(otherwise)
        super().__init__("if", *args)

    def __str__(self) -> str:
        cond, then = self.args[0], self.args[1]
        otherwise = self.args[2] if len(self.args) > 2 else None
        if otherwise is None:
            return f"$(if {cond},{then})"
        return f"$(if {cond},{then},{otherwise})"


class MEval(MFunc):
    """$(eval text) as an expression (expands to empty string at runtime)"""

    def __init__(self, text: MExpr):
        super().__init__("eval", text)


class MShell(MFunc):
    """$(shell text) as an expression"""

    def __init__(self, text: MExpr):
        super().__init__("shell", text)


class MCall(MFunc):
    """$(call name[,arg1[,arg2...]])"""

    def __init__(self, name: MVar, *args: MExpr):
        if not isinstance(name, MVar):
            raise TypeError(f"call name must be MVar, got {type(name).__name__}")
        # Encode macro name as a plain identifier token
        super().__init__("call", MConst(name.name), *args)


class MForeach(MFunc):
    """$(foreach var,list,text)"""

    def __init__(self, var: MVar, items: MExpr, body: MExpr):
        if not isinstance(var, MVar):
            raise TypeError(f"foreach variable must be MVar, got {type(var).__name__}")
        # var is passed as plain identifier, not $(var)
        super().__init__("foreach", MConst(var.name), items, body)


class MNot(VarNot[MakeOps]):
    def __str__(self) -> str:
        # Render NOT via $(if cond,,1)
        return str(MIf(self.child, MConst.false(), MConst.true()))


# ---------- Fill MakeOps table ----------

MakeOps.Const = MConst
MakeOps.Name = MVar
MakeOps.Not = MNot
MakeOps.And = MAnd
MakeOps.Or = MOr
MakeOps.Add = MAdd
# MakeOps.Sub/Mul/Div remain None


# ---------- Convenience namespace (no free functions) ----------

class M:
    """
    Public Makefile expression API.
    Use:
        M.Var, M.Const, M.If, M.Call, M.Eval, M.Shell, M.Foreach
        and helper constructors: M.var(), M.const(), M.all(), M.any(), ...
    """
    If = MIf

    @staticmethod
    def const(val: Any) -> MConst:
        return MConst(val)

    @staticmethod
    def true() -> MConst:
        return MConst.true()

    @staticmethod
    def false() -> MConst:
        return MConst.false()

    @staticmethod
    def var(name: str) -> MVar:
        return MVar(name)

    @staticmethod
    def all(*vars: MVar) -> MExpr:
        acc: MExpr = MConst.true()
        for v in vars:
            acc &= v
        return acc

    @staticmethod
    def any(*vars: MVar) -> MExpr:
        acc: MExpr = MConst.false()
        for v in vars:
            acc |= v
        return acc

    @staticmethod
    def eval(text: MExpr) -> MEval:
        return MEval(text)

    @staticmethod
    def shell(text: MExpr) -> MShell:
        return MShell(text)

    @staticmethod
    def foreach(var: MVar, items: MExpr, body: MExpr) -> MForeach:
        return MForeach(var, items, body)
