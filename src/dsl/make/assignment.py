from abc import ABC, abstractmethod
from typing import Iterator

from dsl.container import SimpleNodeStack
from dsl.content import WordAlignedStack, WordsNode
from dsl.make.var import MExpr, MVar


class MAssignment(WordsNode, ABC):
    """
    VAR op VALUE

    Operators:
      =    recursive
      :=   simple
      ?=   set if not set
      +=   append
    """

    @property
    @abstractmethod
    def op(self) -> str:
        raise NotImplementedError

    def __init__(self, var: MVar, value: MExpr, sep: str = " ") -> None:
        super().__init__(sep=sep)   # important: init WordsNode / Node
        self._var = var
        self._value = value

    @property
    def var(self) -> MVar:
        return self._var

    @property
    def value(self) -> MExpr:
        return self._value

    def __iter__(self) -> Iterator[str]:
        yield str(self.var)
        yield self.op
        yield str(self.value)


class MSet(MAssignment):
    @property
    def op(self) -> str:
        return "="


class MSetImmediate(MAssignment):
    @property
    def op(self) -> str:
        return ":="


class MSetDefault(MAssignment):
    @property
    def op(self) -> str:
        return "?="


class MAppend(MAssignment):
    @property
    def op(self) -> str:
        return "+="


class MAssignmentList(WordAlignedStack[MAssignment]):
    """
    Align a list of assignments on the operator column.

    Example output:

      VAR1   = value1
      LONGER := value2
      X      ?= default
    """
    pass
