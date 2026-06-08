"""
Shared fixtures: a fully-featured "test" Language `T` exposing every expression
type and operator, so the algebra (including arithmetic, which make/kconfig do
not register) can be exercised in isolation.

The __str__ forms are deliberately simple and fully parenthesised so rendering
is unambiguous; most algebra assertions use structural equality (==) rather
than string matching, which is independent of formatting.
"""
import pytest

from dsl import (
    Language,
    VarBool, VarInt, VarString, VarHex, VarName, VarNull,
    VarNot, VarAnd, VarOr, VarAdd, VarSub, VarMul, VarDiv,
)

T = Language("test")


class TBool(VarBool[T]):
    def __str__(self): return "true" if self.value else "false"

class TInt(VarInt[T]):
    def __str__(self): return str(self.value)

class TString(VarString[T]):
    def __str__(self): return f'"{self.value}"'

class THex(VarHex[T]):
    def __str__(self): return f"0x{self.value:X}"

class TName(VarName[T]):
    def __str__(self): return self.name

class TNull(VarNull[T]):
    def __str__(self): return ""

class TNot(VarNot[T]):
    def __str__(self): return f"!{self.child}"

class TAnd(VarAnd[T]):
    def __str__(self): return f"({self.left} & {self.right})"

class TOr(VarOr[T]):
    def __str__(self): return f"({self.left} | {self.right})"

class TAdd(VarAdd[T]):
    def __str__(self): return f"({self.left} + {self.right})"

class TSub(VarSub[T]):
    def __str__(self): return f"({self.left} - {self.right})"

class TMul(VarMul[T]):
    def __str__(self): return f"({self.left} * {self.right})"

class TDiv(VarDiv[T]):
    def __str__(self): return f"({self.left} / {self.right})"

T.validate()


class _Lang:
    """Namespace bundle handed to tests via the `lang` fixture."""
    language = T
    Bool, Int, String, Hex, Name, Null = TBool, TInt, TString, THex, TName, TNull
    Not, And, Or, Add, Sub, Mul, Div = TNot, TAnd, TOr, TAdd, TSub, TMul, TDiv


@pytest.fixture
def lang():
    return _Lang


@pytest.fixture
def abc():
    """Three named symbols A, B, C in language T."""
    return TName("A"), TName("B"), TName("C")
