"""
Make variable assignments.

The operator (=, :=, ?=, +=) is bound via GenericArgsMixin so each
flavour is its own class:

    MSet          = MAssignment["="]   — recursive (lazy) expansion
    MSetImmediate = MAssignment[":="]  — immediate (eager) expansion
    MSetDefault   = MAssignment["?="]  — set only if variable is unset
    MAppend       = MAssignment["+="]  — append to existing value

MAssignmentList feeds a list of MAssignment nodes into WordAlignedStack
so the operators line up in a column:

    CC       =  gcc
    CFLAGS   ?= -O2
    BUILDDIR := build
"""
from typing import Iterator

from dsl.content import WordAlignedStack, WordsNode
from dsl.generic_args import GenericArgsMixin
from dsl.make.var import MExpr, MVar


class MAssignment(GenericArgsMixin,WordsNode):
    """
    VAR op VALUE

    Operators:
      =    recursive
      :=   simple
      ?=   set if not set
      +=   append
    """

    def __init__(self, var: MVar, value: MExpr, sep: str = " ") -> None:
        super().__init__(sep=sep)   # important: init WordsNode / Node
        self._var = var
        self._value = value
        self._op= self.get_arg(0)

    @property
    def op(self) -> str:
        return self._op

    @property
    def var(self) -> MVar:
        return self._var

    @property
    def value(self) -> MExpr:
        return self._value

    def __iter__(self) -> Iterator[str]:
        yield self.var.name
        yield self.op
        yield str(self.value)


MSet=MAssignment["="]
MSetImmediate=MAssignment[":="]
MSetDefault=MAssignment["?="]
MAppend=MAssignment["+="]

class MAssignmentList(WordAlignedStack[MAssignment]):
    """
    Align a list of assignments on the operator column.

    Example output:

      VAR1   = value1
      LONGER := value2
      X      ?= default
    """
    pass
