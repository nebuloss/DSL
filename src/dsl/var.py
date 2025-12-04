from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from typing import (
    Any,
    ClassVar,
    Iterator,
    List,
    Optional,
    Self,
    Tuple,
    Type,
)

from dsl.generic_args import GenericArgsMixin


# =====================================================================
# Language descriptor
# =====================================================================

@dataclass
class LanguageOps:
    """
    Per-language class table. Languages must bind:
      Bool, Name, Not, And, Or

    Optional leaves:
      Null

    Optional binary ops:
      Add, Sub, Mul, Div
    """

    Bool: Type["VarBool"]
    Name: Type["VarName"]
    Not: Type["VarNot"]
    And: Type["VarAnd"]
    Or: Type["VarOr"]

    # Optional Null node (singleton per language)
    Null: Optional[Type["VarNull"]] = None

    # Optional operators. If missing, using that operator raises TypeError.
    Add: Optional[Type["VarAdd"]] = None
    Sub: Optional[Type["VarSub"]] = None
    Mul: Optional[Type["VarMul"]] = None
    Div: Optional[Type["VarDiv"]] = None


# =====================================================================
# Base expression
# =====================================================================

class VarExpr(GenericArgsMixin, ABC):
    """
    Generic expression node. Knows its LanguageOps via generics.
    Provides uniform operator dispatch that consults LanguageOps.
    """

    TYPE: ClassVar[str]          # node kind string

    def __init__(self) -> None:
        # First generic type argument is the LanguageOps
        self.ops: Type[LanguageOps] = self.get_arg(0)

    # ---------- unified operator dispatch ----------

    @classmethod
    def _dispatch_binop(
        cls,
        lhs: Any,
        rhs: Any,
        op_cls: Optional[Type["VarBinaryOp"]],
    ) -> "VarExpr":
        # Let Python handle non-VarExpr operands (reflected ops etc.)
        if not isinstance(lhs, VarExpr) or not isinstance(rhs, VarExpr):
            return NotImplemented

        lhs._check_same_ops(rhs)
        ops = lhs.ops

        # Central Null handling for all binary operators
        null_cls = ops.Null
        if null_cls is not None:
            lhs_is_null = isinstance(lhs, null_cls)
            rhs_is_null = isinstance(rhs, null_cls)

            if lhs_is_null and rhs_is_null:
                return null_cls()
            if lhs_is_null:
                return rhs.simplify()
            if rhs_is_null:
                return lhs.simplify()

        if op_cls is None:
            raise TypeError("This language does not define this operator")

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

    # ---------- language consistency ----------

    def _check_same_ops(self, other: "VarExpr") -> None:
        if self.ops is not other.ops:
            raise TypeError("Cannot combine expressions with different LanguageOps")

    # ---------- structural API ----------

    def __iter__(self) -> Iterator["VarExpr"]:
        """
        Generic child iteration based on common attribute names:
          right, left, child, children.
        Order: right, left, child, then items in children (if present).
        """
        # Right child first (as you requested)
        if hasattr(self, "right"):
            child = getattr(self, "right")
            if isinstance(child, VarExpr):
                yield child

        # Then left
        if hasattr(self, "left"):
            child = getattr(self, "left")
            if isinstance(child, VarExpr):
                yield child

        # Then single child (unary)
        if hasattr(self, "child"):
            child = getattr(self, "child")
            if isinstance(child, VarExpr):
                yield child

        # Then any explicit children list/tuple
        if hasattr(self, "children"):
            children = getattr(self, "children")
            try:
                for c in children:
                    if isinstance(c, VarExpr):
                        yield c
            except TypeError:
                # children exists but is not iterable, ignore
                pass

    @abstractmethod
    def args(self) -> Tuple[Any, ...]:
        """
        Structural payload for this node, excluding TYPE.
        Used by key() as (TYPE, *args()).
        """
        raise NotImplementedError

    def key(self) -> Tuple[Any, ...]:
        """
        Canonical structural key used for:
          - sorting
          - detecting duplicates
          - absorption and contradiction checks
        """
        return (self.TYPE, *self.args())

    @abstractmethod
    def simplify(self) -> "VarExpr":
        """
        Return a simplified version of this node.
        May return self.
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """
        Size of the expression tree in nodes.
        Computed purely from iteration.
        """
        return 1 + sum(len(child) for child in self)

    # ---------- printing ----------

    @abstractmethod
    def __str__(self) -> str:
        """
        Concrete languages define syntax here.
        """
        raise NotImplementedError

    # ---------- equality ----------

    def __eq__(self, other: object) -> bool:
        return isinstance(other, VarExpr) and self.key() == other.key()


# =====================================================================
# Unary / Binary bases
# =====================================================================

class VarUnaryOp(VarExpr):

    def __init__(self, child: VarExpr):
        self.child = child
        super().__init__()
        if self.ops is not child.ops:
            raise TypeError("Mismatched LanguageOps in unary operator")

    def args(self) -> Tuple[Any, ...]:
        # Structural payload is the child key
        return (self.child.key(),)


class VarBinaryOp(VarExpr):

    def __init__(self, left: VarExpr, right: VarExpr):
        self.left = left
        self.right = right
        super().__init__()
        if self.ops is not left.ops or self.ops is not right.ops:
            raise TypeError("Mismatched LanguageOps in binary operator")

    def args(self) -> Tuple[Any, ...]:
        # Default ordered pair
        return (self.left.key(), self.right.key())

    @staticmethod
    def is_negation_pair(a: "VarExpr", b: "VarExpr") -> bool:
        ak = a.key()
        bk = b.key()
        # VarNot will have TYPE "not" and args (child_key,)
        return ak == ("not", bk) or bk == ("not", ak)

    @classmethod
    def rebuild_sorted(
        cls,
        terms: List["VarExpr"],
        empty_val: "VarExpr",
        op_cls: Type["VarBinaryOp"],
    ) -> "VarExpr":
        if not terms:
            return empty_val
        if len(terms) == 1:
            return terms[0]

        ops = terms[0].ops
        for t in terms:
            if t.ops is not ops:
                raise TypeError("Mixed LanguageOps in rebuild")

        terms_sorted = sorted(terms, key=lambda e: e.key())
        acc: VarExpr = terms_sorted[0]
        for t in terms_sorted[1:]:
            acc = op_cls(acc, t)  # type: ignore[arg-type]
        return acc


class VarConcrete(VarExpr):
    """
    Base class for leaf nodes or nodes with no structural children.
    """

    def simplify(self) -> Self:
        return self

    def args(self) -> Tuple[Any, ...]:
        # Default: no payload beyond TYPE
        return ()


# =====================================================================
# Leaves
# =====================================================================

class VarConst(VarConcrete):
    """
    Constant node. Concrete languages implement __str__.
    No arithmetic here. Use LanguageOps Add/Sub/Mul/Div to enable math or concat.
    """

    def __init__(self, val: Any):
        self._val = val
        super().__init__()

    @property
    def value(self):
        return self._val

    def args(self) -> Tuple[Any, ...]:
        # Structural payload is the raw Python value
        return (self._val,)


class VarBool(VarConst):
    TYPE = "bool"

    def __init__(self, val):
        super().__init__(bool(val))

    @classmethod
    def isTrue(cls, x: "VarExpr") -> bool:
        return isinstance(x, cls) and x._val is True

    @classmethod
    def isFalse(cls, x: "VarExpr") -> bool:
        return isinstance(x, cls) and x._val is False

    @classmethod
    def true(cls) -> Self:
        return cls(True)  # type: ignore[call-arg]

    @classmethod
    def false(cls) -> Self:
        return cls(False)  # type: ignore[call-arg]


class VarString(VarConst):
    TYPE = "string"

    def __init__(self, val):
        super().__init__(str(val))


class VarInt(VarConst):
    TYPE = "int"

    def __init__(self, val):
        super().__init__(int(val))


class VarName(VarConcrete):
    TYPE = "name"
    """
    Variable reference.

    By default, variable names may contain ASCII letters, digits, underscore,
    and dot. Extra allowed characters can be passed with `special_chars`.
    """

    # Base allowed characters: letters, digits, underscore, dot
    _BASE_ALLOWED = "A-Za-z0-9_."
    _ILLEGAL_CHAR_RE = re.compile(rf"[^{_BASE_ALLOWED}]")

    def __init__(self, name: str, special_chars: str = ""):
        if not isinstance(name, str):
            raise TypeError("Variable name must be a string")

        s = name.strip()
        if not s:
            raise ValueError("Empty variable name")

        # Replace spaces with underscore
        s = s.replace(" ", "_")

        # Build a regex that treats special_chars as extra allowed characters
        self._special_chars = special_chars
        if special_chars:
            extra = re.escape(special_chars)
            klass = type(self)
            illegal_re = re.compile(rf"[^{klass._BASE_ALLOWED}{extra}]")
        else:
            illegal_re = type(self)._ILLEGAL_CHAR_RE

        # Check for any remaining illegal characters
        m = illegal_re.search(s)
        if m:
            illegal = m.group(0)
            raise ValueError(f"Illegal character {illegal!r} in variable name")

        self._name = s
        super().__init__()

    @property
    def name(self) -> str:
        return self._name

    def args(self) -> Tuple[Any, ...]:
        # key(): ("name", "x")
        return (self._name,)

    def add_prefix(self, prefix: str) -> Self:
        # Preserve the same special_chars for derived names
        return type(self)(f"{prefix}_{self.name}", special_chars=self._special_chars)

    def add_suffix(self, suffix: str) -> Self:
        # Preserve the same special_chars for derived names
        return type(self)(f"{self.name}_{suffix}", special_chars=self._special_chars)


class VarNull(VarConcrete):
    TYPE = "null"
    """
    Singleton sentinel node for "no expression".

    Concrete languages must subclass this.
    Each concrete VarNull subclass is a singleton.
    """

    _instance: Optional["VarNull"] = None

    def __new__(cls) -> "VarNull":
        if cls is VarNull:
            raise TypeError("VarNull must be subclassed per language")
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        super().__init__()

    def args(self) -> Tuple[Any, ...]:
        # No payload
        return ()

    @classmethod
    def isNull(cls, expr: "VarExpr") -> bool:
        return isinstance(expr, cls)


# =====================================================================
# Logic
# =====================================================================

class VarNot(VarUnaryOp):
    PREC = 3
    TYPE = "not"

    def simplify(self) -> "VarExpr":
        c = self.child

        if self.ops.Bool.isTrue(c):
            return self.ops.Bool.false()
        if self.ops.Bool.isFalse(c):
            return self.ops.Bool.true()

        if isinstance(c, self.ops.Not):
            # ~~X => X
            return c.child

        if isinstance(c, self.ops.And):
            # De Morgan
            return (self.ops.Not(c.left) | self.ops.Not(c.right)).simplify()

        if isinstance(c, self.ops.Or):
            # De Morgan
            return (self.ops.Not(c.left) & self.ops.Not(c.right)).simplify()

        # Nothing more to do structurally
        return self.ops.Not(c)


class VarAnd(VarBinaryOp):
    TYPE = "and"

    def simplify(self) -> "VarExpr":
        left = self.left
        right = self.right

        if self.ops.Bool.isFalse(left) or self.ops.Bool.isFalse(right):
            return self.ops.Bool.false()
        if self.ops.Bool.isTrue(left):
            return right
        if self.ops.Bool.isTrue(right):
            return left
        if left.key() == right.key():
            return left
        if VarBinaryOp.is_negation_pair(left, right):
            return self.ops.Bool.false()

        terms = self._flatten_terms(left, right)

        early = self._detect_contradiction(terms)
        if early is not None:
            return early

        terms = self._absorption_with_or(terms)
        terms = self._negated_absorption_with_or(terms)

        return VarBinaryOp.rebuild_sorted(
            terms,
            self.ops.Bool.true(),
            self.ops.And,
        )

    # helpers use self.ops directly
    def _flatten_terms(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        items: List[VarExpr] = []
        seen = set()

        def add(e: VarExpr) -> None:
            if self.ops.Bool.isTrue(e):
                return
            k = e.key()
            if k not in seen:
                seen.add(k)
                items.append(e)

        def walk(e: VarExpr) -> None:
            if isinstance(e, self.ops.And):
                walk(e.left)
                walk(e.right)
            else:
                add(e)

        walk(a)
        walk(b)
        return items

    def _detect_contradiction(self, terms: List[VarExpr]) -> Optional[VarExpr]:
        keys = {t.key() for t in terms}
        for t in terms:
            if isinstance(t, self.ops.Not) and t.child.key() in keys:
                return self.ops.Bool.false()
            if not isinstance(t, self.ops.Not) and ("not", t.key()) in keys:
                return self.ops.Bool.false()
        return None

    def _absorption_with_or(self, terms: List[VarExpr]) -> List[VarExpr]:
        if not terms:
            return terms
        base = {t.key() for t in terms}
        kept: List[VarExpr] = []
        for t in terms:
            if isinstance(t, self.ops.Or) and (t.left.key() in base or t.right.key() in base):
                continue
            kept.append(t)
        return kept

    def _negated_absorption_with_or(self, terms: List[VarExpr]) -> List[VarExpr]:
        if len(terms) <= 1:
            return terms

        base_pos = {t.key() for t in terms if not isinstance(t, self.ops.Not)}
        base_neg = {t.child.key() for t in terms if isinstance(t, self.ops.Not)}

        new_terms: List[VarExpr] = []
        changed = False

        for t in terms:
            if isinstance(t, self.ops.Or):
                l, r = t.left, t.right

                if isinstance(l, self.ops.Not) and l.child.key() in base_pos:
                    new_terms.append(r)
                    changed = True
                    continue
                if isinstance(r, self.ops.Not) and r.child.key() in base_pos:
                    new_terms.append(l)
                    changed = True
                    continue

                if l.key() in base_neg:
                    new_terms.append(r)
                    changed = True
                    continue
                if r.key() in base_neg:
                    new_terms.append(l)
                    changed = True
                    continue

            new_terms.append(t)

        return new_terms if changed else terms


class VarOr(VarBinaryOp):
    TYPE = "or"

    def simplify(self) -> "VarExpr":
        left = self.left
        right = self.right

        if self.ops.Bool.isTrue(left) or self.ops.Bool.isTrue(right):
            return self.ops.Bool.true()
        if self.ops.Bool.isFalse(left):
            return right
        if self.ops.Bool.isFalse(right):
            return left
        if left.key() == right.key():
            return left
        if VarBinaryOp.is_negation_pair(left, right):
            return self.ops.Bool.true()

        terms = self._flatten_terms(left, right)

        early = self._detect_tautology(terms)
        if early is not None:
            return early

        terms = self._absorption_with_and(terms)
        terms = self._negated_absorption_with_and(terms)

        return VarBinaryOp.rebuild_sorted(
            terms,
            self.ops.Bool.false(),
            self.ops.Or,
        )

    # helpers use self.ops directly
    def _flatten_terms(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        items: List[VarExpr] = []
        seen = set()

        def add(e: VarExpr) -> None:
            if self.ops.Bool.isFalse(e):
                return
            k = e.key()
            if k not in seen:
                seen.add(k)
                items.append(e)

        def walk(e: VarExpr) -> None:
            if isinstance(e, self.ops.Or):
                walk(e.left)
                walk(e.right)
            else:
                add(e)

        walk(a)
        walk(b)
        return items

    def _detect_tautology(self, terms: List[VarExpr]) -> Optional[VarExpr]:
        keys = {t.key() for t in terms}
        for t in terms:
            if isinstance(t, self.ops.Not) and t.child.key() in keys:
                return self.ops.Bool.true()
            if not isinstance(t, self.ops.Not) and ("not", t.key()) in keys:
                return self.ops.Bool.true()
        return None

    def _absorption_with_and(self, terms: List[VarExpr]) -> List[VarExpr]:
        if not terms:
            return terms
        base = {t.key() for t in terms}
        kept: List[VarExpr] = []
        for t in terms:
            if isinstance(t, self.ops.And) and (t.left.key() in base or t.right.key() in base):
                continue
            kept.append(t)
        return kept

    def _negated_absorption_with_and(self, terms: List[VarExpr]) -> List[VarExpr]:
        if len(terms) <= 1:
            return terms

        base_pos = {t.key() for t in terms if not isinstance(t, self.ops.Not)}
        base_neg = {t.child.key() for t in terms if isinstance(t, self.ops.Not)}

        new_terms: List[VarExpr] = []
        changed = False

        for t in terms:
            if isinstance(t, self.ops.And):
                l, r = t.left, t.right

                if isinstance(l, self.ops.Not) and l.child.key() in base_pos:
                    new_terms.append(r)
                    changed = True
                    continue
                if isinstance(r, self.ops.Not) and r.child.key() in base_pos:
                    new_terms.append(l)
                    changed = True
                    continue

                if l.key() in base_neg:
                    new_terms.append(r)
                    changed = True
                    continue
                if r.key() in base_neg:
                    new_terms.append(l)
                    changed = True
                    continue

            new_terms.append(t)

        return new_terms if changed else terms


# =====================================================================
# Arithmetic and concat operator base classes
# =====================================================================

class VarAdd(VarBinaryOp):
    TYPE = "add"


class VarSub(VarBinaryOp):
    TYPE = "sub"


class VarMul(VarBinaryOp):
    TYPE = "mul"


class VarDiv(VarBinaryOp):
    TYPE = "div"
