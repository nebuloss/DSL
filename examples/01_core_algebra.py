"""
Core expression algebra: Language binding, all expression types, simplification.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dsl import Language, VarBool, VarInt, VarString, VarHex, VarName, VarNull
from dsl import VarNot, VarAnd, VarOr, VarAdd, VarSub, VarMul, VarDiv

# ── Define a toy language with all types and ops ─────────────────────────────

lang = Language("demo")

class DBool(VarBool[lang]):
    def __str__(self): return "true" if self.value else "false"

class DInt(VarInt[lang]):
    def __str__(self): return str(self.value)

class DString(VarString[lang]):
    def __str__(self): return f'"{self.value}"'

class DHex(VarHex[lang]):
    def __str__(self): return f"0x{self.value:X}"

class DName(VarName[lang]):
    def __str__(self): return self.name

class DNull(VarNull[lang]):
    def __str__(self): return "(null)"

class DNot(VarNot[lang]):
    def __str__(self): return f"!{self.child}"

class DAnd(VarAnd[lang]):
    def __str__(self): return f"({self.left} && {self.right})"

class DOr(VarOr[lang]):
    def __str__(self): return f"({self.left} || {self.right})"

class DAdd(VarAdd[lang]):
    def __str__(self): return f"({self.left} + {self.right})"

class DSub(VarSub[lang]):
    def __str__(self): return f"({self.left} - {self.right})"

class DMul(VarMul[lang]):
    def __str__(self): return f"({self.left} * {self.right})"

class DDiv(VarDiv[lang]):
    def __str__(self): return f"({self.left} / {self.right})"

lang.validate()

# ── Leaves ───────────────────────────────────────────────────────────────────

print("=== Leaf types ===")
print("DBool(True) :", DBool(True))
print("DBool(False):", DBool(False))
print("DBool.true():", DBool.true())
print("DBool.false():", DBool.false())
print("DInt(42)    :", DInt(42))
print("DString(hi) :", DString("hi"))
print("DHex(0xFF)  :", DHex(0xFF))
print("DName(foo)  :", DName("foo"))
print("DNull()     :", DNull())
print()

# ── Boolean simplification ───────────────────────────────────────────────────

print("=== Boolean simplification ===")
A, B, C = DName("A"), DName("B"), DName("C")

print("A & A            =>", A & A)          # idempotent: A
print("A | A            =>", A | A)          # idempotent: A
print("A & true         =>", A & DBool.true())    # absorption: A
print("A | false        =>", A | DBool.false())   # absorption: A
print("A & false        =>", A & DBool.false())   # annihilation: false
print("A | true         =>", A | DBool.true())    # annihilation: true
print("A & ~A           =>", A & ~A)         # contradiction: false
print("A | ~A           =>", A | ~A)         # tautology: true
print("~~A              =>", ~~A)            # double negation: A
print("~(A & B)         =>", ~(A & B))       # De Morgan: !A || !B
print("~(A | B)         =>", ~(A | B))       # De Morgan: !A && !B
# Absorption: A & (A | B) => A
print("A & (A | B)      =>", A & (A | B))
# Absorption: A | (A & B) => A
print("A | (A & B)      =>", A | (A & B))
print()

# ── Arithmetic simplification ────────────────────────────────────────────────

print("=== Arithmetic simplification ===")
x, y = DName("x"), DName("y")
two = DInt(2)
three = DInt(3)

print("2 + 3            =>", DInt(2) + DInt(3))   # constant folding: 5
print("x + x            =>", x + x)                # coeff merge: 2*x
print("x + x + x        =>", x + x + x)            # 3*x
print("2*x + 3*x        =>", (two * x) + (three * x))  # 5*x
print("x - x            =>", x - x)                # 0
print("x - 0            =>", x - DInt(0))          # x
print("6 / 2            =>", DInt(6) / DInt(2))    # constant folding: 3
print("0 * x            =>", DInt(0) * x)          # annihilation: 0
print("(4*x) / 2        =>", (DInt(4) * x) / DInt(2))  # 2*x
print()

# ── Null propagation ─────────────────────────────────────────────────────────

print("=== Null propagation ===")
null = DNull()
print("null | A         =>", null | A)    # A
print("A | null         =>", A | null)    # A
print("null & A         =>", null & A)    # A  (null identity for |, same for &)
print("null | null      =>", null | null) # null
print()

# ── Equality and key-based deduplication ─────────────────────────────────────

print("=== Structural equality ===")
print("DName('x') == DName('x'):", DName("x") == DName("x"))
print("DName('x') == DName('y'):", DName("x") == DName("y"))
print("DAnd(A,B)  == DAnd(A,B) :", DAnd(A, B) == DAnd(A, B))
print()

# ── Tree size ────────────────────────────────────────────────────────────────

print("=== Tree size (len) ===")
expr = (A & B) | (~C & A)
print(f"(A & B) | (~C & A) has {len(expr)} nodes")
print()
