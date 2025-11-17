from typing import Any, List, Optional
from dsl.make.var import MConst, MExpr, MVar, MakeOps
from dsl.var import VarExpr

class MFunction(VarExpr[MakeOps]):
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

class MIf(MFunction):
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


class MEval(MFunction):
    """$(eval text) as an expression (expands to empty string at runtime)"""

    def __init__(self, text: MExpr):
        super().__init__("eval", text)


class MShell(MFunction):
    """$(shell text) as an expression"""

    def __init__(self, text: MExpr):
        super().__init__("shell", text)


class MCall(MFunction):
    """$(call name[,arg1[,arg2...]])"""

    def __init__(self, name: MVar, *args: MExpr):
        if not isinstance(name, MVar):
            raise TypeError(f"call name must be MVar, got {type(name).__name__}")
        # Encode macro name as a plain identifier token
        super().__init__("call", MConst(name.name), *args)


class MForeach(MFunction):
    """$(foreach var,list,text)"""

    def __init__(self, var: MVar, items: MExpr, body: MExpr):
        if not isinstance(var, MVar):
            raise TypeError(f"foreach variable must be MVar, got {type(var).__name__}")
        # var is passed as plain identifier, not $(var)
        super().__init__("foreach", MConst(var.name), items, body)
