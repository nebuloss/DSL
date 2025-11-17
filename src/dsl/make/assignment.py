from dsl.lang import Text, WordAlignedStack
from dsl.make.var import MExpr, MVar


class MAssignment(Text):
    """
    VAR op VALUE

    Operators:
      =    recursive
      :=   simple
      ?=   set if not set
      +=   append
    """

    def __init__(self, var: MVar, value: MExpr, op: str = "="):
        op = op.strip()
        if op not in ("=", ":=", "?=", "+="):
            raise ValueError(f"Invalid assignment operator: {op}")
        super().__init__(f"{var.name} {op} {value}")


class MSet(MAssignment):
    def __init__(self, var: MVar, value: MExpr):
        super().__init__(var, value, "=")

class MSetImmediate(MAssignment):
    def __init__(self, var: MVar, value: MExpr):
        super().__init__(var, value, ":=")

class MSetDefault(MAssignment):
    def __init__(self, var: MVar, value: MExpr):
        super().__init__(var, value, "?=")

class MAppend(MAssignment):
    def __init__(self, var: MVar, value: MExpr):
        super().__init__(var, value, "+=")

class MAssignmentList(WordAlignedStack[MAssignment]):
    def __init__(self,*assignments:MAssignment):
        super().__init__(*assignments,limit=2)
