from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    ClassVar,
    Generic,
    List,
    Optional,
    Self,
    Tuple,
    Type,
    TypeVar,
    get_args,
)


# =====================================================================
# Language descriptor
# =====================================================================

@dataclass
class LanguageOps:
    """
    Per-language class table. Languages must bind:
      Const, Name, Not, And, Or

    Optional leaves:
      Null

    Optional binary ops:
      Add, Sub, Mul, Div
    """

    Const: Type["VarConst"]
    Name:  Type["VarName"]
    Not:   Type["VarNot"]
    And:   Type["VarAnd"]
    Or:    Type["VarOr"]

    # Optional Null node (singleton per language)
    Null: Optional[Type["VarNull"]] = None

    # Optional operators. If missing, using that operator raises TypeError.
    Add: Optional[Type["VarAdd"]] = None
    Sub: Optional[Type["VarSub"]] = None
    Mul: Optional[Type["VarMul"]] = None
    Div: Optional[Type["VarDiv"]] = None


OpsT = TypeVar("OpsT", bound=LanguageOps)


# =====================================================================
# Base expression
# =====================================================================

class VarExpr(Generic[OpsT], ABC):
    """
    Generic expression node. Knows its LanguageOps via generics.
    Provides uniform operator dispatch that consults LanguageOps.
    """

    def __init__(self):
        self.ops: Type[LanguageOps] = self._resolve_ops()

    # ---------- unified operator dispatch ----------

    @classmethod
    def _dispatch_binop(
        cls,
        lhs: "VarExpr",
        rhs: "VarExpr",
        op_cls: Optional[Type["VarBinaryOp"]],
    ) -> "VarExpr":
        if not isinstance(rhs, VarExpr):
            return NotImplemented  # let Python try reflected op

        lhs._check_same_ops(rhs)
        ops = lhs.ops

        # Central Null handling for all binary operators
        null_cls = ops.Null
        if null_cls is not None:
            lhs_is_null = isinstance(lhs, null_cls)
            rhs_is_null = isinstance(rhs, null_cls)

            if lhs_is_null and rhs_is_null:
                # Collapse Null op Null to the singleton
                return null_cls()
            if lhs_is_null:
                # Null op X -> simplified X
                return rhs.simplify()
            if rhs_is_null:
                # X op Null -> simplified X
                return lhs.simplify()

        if op_cls is None:
            # Map the operator class to a printable token for the error
            op_map = {
                ops.And: "&",
                ops.Or: "|",
                ops.Add: "+",
                ops.Sub: "-",
                ops.Mul: "*",
                ops.Div: "/",
            }
            token = op_map.get(op_cls, "?")
            raise TypeError(f"This language does not define operator '{token}'")

        return op_cls(lhs.simplify(), rhs.simplify()).simplify()  # type: ignore[call-arg]

    # ---------- Python operator methods ----------

    # Boolean logic via bitwise ops
    def __or__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Or)

    def __ror__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(other, self, self.ops.Or)

    def __ior__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Or)

    def __and__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.And)

    def __rand__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(other, self, self.ops.And)

    def __iand__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.And)

    def __invert__(self) -> "VarExpr":
        # Central Null handling for unary not
        ops = self.ops
        null_cls = ops.Null
        if null_cls is not None and isinstance(self, null_cls):
            return self
        return ops.Not(self.simplify()).simplify()

    # Arithmetic and concat (language optional)
    def __add__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Add)

    def __radd__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(other, self, self.ops.Add)

    def __iadd__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Add)

    def __sub__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Sub)

    def __rsub__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(other, self, self.ops.Sub)

    def __isub__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Sub)

    def __mul__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Mul)

    def __rmul__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(other, self, self.ops.Mul)

    def __imul__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Mul)

    def __truediv__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Div)

    def __rtruediv__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(other, self, self.ops.Div)

    def __itruediv__(self, other: "VarExpr") -> "VarExpr":
        return type(self)._dispatch_binop(self, other, self.ops.Div)

    # ---------- resolve LanguageOps from generics ----------

    def _resolve_ops(self) -> Type[LanguageOps]:
        # Instance-level generic
        orig = getattr(self, "__orig_class__", None)
        if orig is not None:
            args = get_args(orig)
            if args:
                cand = args[0]
                if self._is_valid_ops(cand):
                    return cand

        # Class-level bases
        for base in getattr(type(self), "__orig_bases__", ()):
            args = get_args(base)
            if args:
                cand = args[0]
                if self._is_valid_ops(cand):
                    return cand

        raise TypeError(
            f"Could not resolve LanguageOps for {type(self).__name__}. "
            "Declare your node as VarExpr[YourOps] and bind YourOps table."
        )

    @staticmethod
    def _is_valid_ops(cand: Any) -> bool:
        if not isinstance(cand, type):
            return False
        if not issubclass(cand, LanguageOps):
            return False
        required = ("Const", "Name", "Not", "And", "Or")
        for attr in required:
            if getattr(cand, attr, None) is None:
                return False
        return True  # Add/Sub/Mul/Div are optional

    # ---------- language consistency ----------

    def _check_same_ops(self, other: "VarExpr") -> None:
        if self.ops is not other.ops:
            raise TypeError("Cannot combine expressions with different LanguageOps")

    # ---------- structural API ----------

    @abstractmethod
    def key(self) -> Tuple[Any, ...]:
        pass

    @abstractmethod
    def simplify(self) -> "VarExpr":
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass

    # ---------- printing ----------

    @abstractmethod
    def __str__(self) -> str:
        pass

    # ---------- equality ----------

    def __eq__(self, other: "VarExpr") -> bool:
        return isinstance(other, VarExpr) and str(self) == str(other)


# =====================================================================
# Unary / Binary bases
# =====================================================================

class VarUnaryOp(VarExpr[OpsT], ABC):
    PREC: ClassVar[int] = 0

    def __init__(self, child: VarExpr[OpsT]):
        self.child = child
        super().__init__()
        if self.ops is not child.ops:
            raise TypeError("Mismatched LanguageOps in unary operator")

    @property
    def prec(self) -> int:
        return self.PREC


class VarBinaryOp(VarExpr[OpsT], ABC):
    PREC: ClassVar[int] = 0

    def __init__(self, left: VarExpr[OpsT], right: VarExpr[OpsT]):
        self.left = left
        self.right = right
        super().__init__()
        if self.ops is not left.ops or self.ops is not right.ops:
            raise TypeError("Mismatched LanguageOps in binary operator")

    @property
    def prec(self) -> int:
        return self.PREC

    @staticmethod
    def is_negation_pair(a: "VarExpr[OpsT]", b: "VarExpr[OpsT]") -> bool:
        ak = a.key()
        bk = b.key()
        return ak == ("not", bk) or bk == ("not", ak)

    @classmethod
    def rebuild_sorted(
        cls,
        terms: List["VarExpr[OpsT]"],
        empty_val: "VarExpr[OpsT]",
        op_cls: Type["VarBinaryOp[OpsT]"],
    ) -> "VarExpr[OpsT]":
        if not terms:
            return empty_val
        if len(terms) == 1:
            return terms[0]

        ops = terms[0].ops
        for t in terms:
            if t.ops is not ops:
                raise TypeError("Mixed LanguageOps in rebuild")

        terms_sorted = sorted(terms, key=lambda e: e.key())
        acc: VarExpr[OpsT] = terms_sorted[0]
        for t in terms_sorted[1:]:
            acc = op_cls(acc, t)  # type: ignore[arg-type]
        return acc


# =====================================================================
# Leaves
# =====================================================================

class VarConst(VarExpr[OpsT], ABC):
    """
    Constant node. Concrete languages implement __str__.
    No arithmetic here. Use LanguageOps Add/Sub/Mul/Div to enable math or concat.
    """

    def __init__(self, val: Any):
        self.val = val
        super().__init__()

    def key(self) -> Tuple[Any, ...]:
        return ("const", self.val)

    def simplify(self) -> "VarExpr[OpsT]":
        return self

    def __len__(self) -> int:
        return 0

    @classmethod
    def isTrue(cls, x: "VarExpr[OpsT]") -> bool:
        return isinstance(x, cls) and x.val is True

    @classmethod
    def isFalse(cls, x: "VarExpr[OpsT]") -> bool:
        return isinstance(x, cls) and x.val is False

    @classmethod
    def true(cls) -> "VarConst[OpsT]":
        return cls(True)  # type: ignore[call-arg]

    @classmethod
    def false(cls) -> "VarConst[OpsT]":
        return cls(False)  # type: ignore[call-arg]


class VarName(VarExpr[OpsT], ABC):
    """
    Variable reference. Concrete languages may override normalize.
    """

    def __init__(self, name: str):
        self._name = self.normalize(name)
        super().__init__()

    @staticmethod
    def normalize(name: str) -> str:
        if not isinstance(name, str):
            raise TypeError("Variable name must be a string")
        s = name.strip()
        if not s:
            raise ValueError("Empty variable name")
        return s

    @property
    def name(self) -> str:
        return self._name

    def key(self) -> Tuple[Any, ...]:
        return ("name", self._name)

    def simplify(self) -> "VarExpr[OpsT]":
        return self

    def __len__(self) -> int:
        return 1

    def add_prefix(self, prefix: str) -> Self:
        return type(self)(f"{prefix}_{self.name}")

    def add_suffix(self, suffix: str) -> Self:
        return type(self)(f"{self.name}_{suffix}")


class VarNull(VarExpr[OpsT], ABC):
    """
    Singleton sentinel node for "no expression".

    Concrete languages must subclass this and implement __str__.
    Each concrete VarNull subclass is a singleton.
    """

    _instance: ClassVar[Optional["VarNull[OpsT]"]] = None

    def __new__(cls) -> "VarNull[OpsT]":
        if cls is VarNull:
            raise TypeError("VarNull must be subclassed per language")
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def isNull(cls, expr: "VarExpr[OpsT]") -> bool:
        return isinstance(expr, cls)

    def key(self) -> Tuple[Any, ...]:
        return ("null",)

    def simplify(self) -> "VarExpr[OpsT]":
        return self

    def __len__(self) -> int:
        return 0

    @abstractmethod
    def __str__(self) -> str:
        ...


# =====================================================================
# Logic
# =====================================================================

class VarNot(VarUnaryOp[OpsT], ABC):
    PREC = 3

    def key(self) -> Tuple[Any, ...]:
        return ("not", self.child.key())

    def simplify(self) -> "VarExpr[OpsT]":
        c = self.child

        if self.ops.Const.isTrue(c):
            return self.ops.Const.false()
        if self.ops.Const.isFalse(c):
            return self.ops.Const.true()

        if isinstance(c, self.ops.Not):
            return c.child

        if isinstance(c, self.ops.And):
            return (self.ops.Not(c.left) | self.ops.Not(c.right)).simplify()

        if isinstance(c, self.ops.Or):
            return (self.ops.Not(c.left) & self.ops.Not(c.right)).simplify()

        return self.ops.Not(c)

    def __len__(self) -> int:
        return len(self.child)


class VarAnd(VarBinaryOp[OpsT], ABC):
    PREC = 2

    def key(self) -> Tuple[Any, ...]:
        flat = self._flatten_terms(self.left, self.right)
        keys = sorted(t.key() for t in flat)
        return ("and", tuple(keys))

    def simplify(self) -> "VarExpr[OpsT]":
        left = self.left
        right = self.right

        if self.ops.Const.isFalse(left) or self.ops.Const.isFalse(right):
            return self.ops.Const.false()
        if self.ops.Const.isTrue(left):
            return right
        if self.ops.Const.isTrue(right):
            return left
        if left.key() == right.key():
            return left
        if VarBinaryOp.is_negation_pair(left, right):
            return self.ops.Const.false()

        terms = self._flatten_terms(left, right)

        early = self._detect_contradiction(terms)
        if early is not None:
            return early

        terms = self._absorption_with_or(terms)
        terms = self._negated_absorption_with_or(terms)

        return VarBinaryOp.rebuild_sorted(
            terms,
            self.ops.Const.true(),
            self.ops.And,
        )

    def __len__(self) -> int:
        return len(self.left) + len(self.right)

    # helpers use self.ops directly
    def _flatten_terms(self, a: VarExpr[OpsT], b: VarExpr[OpsT]) -> List[VarExpr[OpsT]]:
        items: List[VarExpr[OpsT]] = []
        seen = set()

        def add(e: VarExpr[OpsT]) -> None:
            if self.ops.Const.isTrue(e):
                return
            k = e.key()
            if k not in seen:
                seen.add(k)
                items.append(e)

        def walk(e: VarExpr[OpsT]) -> None:
            if isinstance(e, self.ops.And):
                walk(e.left)
                walk(e.right)
            else:
                add(e)

        walk(a)
        walk(b)
        return items

    def _detect_contradiction(self, terms: List[VarExpr[OpsT]]) -> Optional[VarExpr[OpsT]]:
        keys = {t.key() for t in terms}
        for t in terms:
            if isinstance(t, self.ops.Not) and t.child.key() in keys:
                return self.ops.Const.false()
            if not isinstance(t, self.ops.Not) and ("not", t.key()) in keys:
                return self.ops.Const.false()
        return None

    def _absorption_with_or(self, terms: List[VarExpr[OpsT]]) -> List[VarExpr[OpsT]]:
        if not terms:
            return terms
        base = {t.key() for t in terms}
        kept: List[VarExpr[OpsT]] = []
        for t in terms:
            if isinstance(t, self.ops.Or) and (t.left.key() in base or t.right.key() in base):
                continue
            kept.append(t)
        return kept

    def _negated_absorption_with_or(self, terms: List[VarExpr[OpsT]]) -> List[VarExpr[OpsT]]:
        if len(terms) <= 1:
            return terms

        base_pos = {t.key() for t in terms if not isinstance(t, self.ops.Not)}
        base_neg = {t.child.key() for t in terms if isinstance(t, self.ops.Not)}

        new_terms: List[VarExpr[OpsT]] = []
        changed = False

        for t in terms:
            if isinstance(t, self.ops.Or):
                l, r = t.left, t.right

                if isinstance(l, self.ops.Not) and l.child.key() in base_pos:
                    new_terms.append(r); changed = True; continue
                if isinstance(r, self.ops.Not) and r.child.key() in base_pos:
                    new_terms.append(l); changed = True; continue

                if l.key() in base_neg:
                    new_terms.append(r); changed = True; continue
                if r.key() in base_neg:
                    new_terms.append(l); changed = True; continue

            new_terms.append(t)

        return new_terms if changed else terms


class VarOr(VarBinaryOp[OpsT], ABC):
    PREC = 1

    def key(self) -> Tuple[Any, ...]:
        flat = self._flatten_terms(self.left, self.right)
        keys = sorted(t.key() for t in flat)
        return ("or", tuple(keys))

    def simplify(self) -> "VarExpr[OpsT]":
        left = self.left
        right = self.right

        if self.ops.Const.isTrue(left) or self.ops.Const.isTrue(right):
            return self.ops.Const.true()
        if self.ops.Const.isFalse(left):
            return right
        if self.ops.Const.isFalse(right):
            return left
        if left.key() == right.key():
            return left
        if VarBinaryOp.is_negation_pair(left, right):
            return self.ops.Const.true()

        terms = self._flatten_terms(left, right)

        early = self._detect_tautology(terms)
        if early is not None:
            return early

        terms = self._absorption_with_and(terms)
        terms = self._negated_absorption_with_and(terms)

        return VarBinaryOp.rebuild_sorted(
            terms,
            self.ops.Const.false(),
            self.ops.Or,
        )

    def __len__(self) -> int:
        return len(self.left) + len(self.right)

    # helpers use self.ops directly
    def _flatten_terms(self, a: VarExpr[OpsT], b: VarExpr[OpsT]) -> List[VarExpr[OpsT]]:
        items: List[VarExpr[OpsT]] = []
        seen = set()

        def add(e: VarExpr[OpsT]) -> None:
            if self.ops.Const.isFalse(e):
                return
            k = e.key()
            if k not in seen:
                seen.add(k)
                items.append(e)

        def walk(e: VarExpr[OpsT]) -> None:
            if isinstance(e, self.ops.Or):
                walk(e.left)
                walk(e.right)
            else:
                add(e)

        walk(a)
        walk(b)
        return items

    def _detect_tautology(self, terms: List[VarExpr[OpsT]]) -> Optional[VarExpr[OpsT]]:
        keys = {t.key() for t in terms}
        for t in terms:
            if isinstance(t, self.ops.Not) and t.child.key() in keys:
                return self.ops.Const.true()
            if not isinstance(t, self.ops.Not) and ("not", t.key()) in keys:
                return self.ops.Const.true()
        return None

    def _absorption_with_and(self, terms: List[VarExpr[OpsT]]) -> List[VarExpr[OpsT]]:
        if not terms:
            return terms
        base = {t.key() for t in terms}
        kept: List[VarExpr[OpsT]] = []
        for t in terms:
            if isinstance(t, self.ops.And) and (t.left.key() in base or t.right.key() in base):
                continue
            kept.append(t)
        return kept

    def _negated_absorption_with_and(self, terms: List[VarExpr[OpsT]]) -> List[VarExpr[OpsT]]:
        if len(terms) <= 1:
            return terms

        base_pos = {t.key() for t in terms if not isinstance(t, self.ops.Not)}
        base_neg = {t.child.key() for t in terms if isinstance(t, self.ops.Not)}

        new_terms: List[VarExpr[OpsT]] = []
        changed = False

        for t in terms:
            if isinstance(t, self.ops.And):
                l, r = t.left, t.right

                if isinstance(l, self.ops.Not) and l.child.key() in base_pos:
                    new_terms.append(r); changed = True; continue
                if isinstance(r, self.ops.Not) and r.child.key() in base_pos:
                    new_terms.append(l); changed = True; continue

                if l.key() in base_neg:
                    new_terms.append(r); changed = True; continue
                if r.key() in base_neg:
                    new_terms.append(l); changed = True; continue

            new_terms.append(t)

        return new_terms if changed else terms


# =====================================================================
# Arithmetic and concat operator base classes
# =====================================================================

class VarAdd(VarBinaryOp[OpsT], ABC):
    PREC: ClassVar[int] = 4

    def key(self) -> Tuple[Any, ...]:
        return ("add", self.left.key(), self.right.key())

    def simplify(self) -> "VarExpr[OpsT]":
        return self  # type: ignore[call-arg]


class VarSub(VarBinaryOp[OpsT], ABC):
    PREC: ClassVar[int] = 4

    def key(self) -> Tuple[Any, ...]:
        return ("sub", self.left.key(), self.right.key())

    def simplify(self) -> "VarExpr[OpsT]":
        return self  # type: ignore[call-arg]


class VarMul(VarBinaryOp[OpsT], ABC):
    PREC: ClassVar[int] = 5

    def key(self) -> Tuple[Any, ...]:
        return ("mul", self.left.key(), self.right.key())

    def simplify(self) -> "VarExpr[OpsT]":
        return self  # type: ignore[call-arg]


class VarDiv(VarBinaryOp[OpsT], ABC):
    PREC: ClassVar[int] = 5

    def key(self) -> Tuple[Any, ...]:
        return ("div", self.left.key(), self.right.key())

    def simplify(self) -> "VarExpr[OpsT]":
        return self
