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
class LanguageTypes:
    # Required
    Bool: Type["VarBool"]
    Name: Type["VarName"]

    # Optional
    Null: Optional[Type["VarNull"]] = None
    Int: Optional[Type["VarInt"]] = None
    String: Optional[Type["VarString"]] = None


@dataclass
class LanguageOps:
    # Required
    Not: Type["VarNot"]
    And: Type["VarAnd"]
    Or: Type["VarOr"]

    # Optional
    Add: Optional[Type["VarAdd"]] = None
    Sub: Optional[Type["VarSub"]] = None
    Mul: Optional[Type["VarMul"]] = None
    Div: Optional[Type["VarDiv"]] = None


class Language:
    """
    Marker base for language descriptors.

    Concrete languages must set:
      types: LanguageTypes
      ops:   LanguageOps
    as class attributes.
    """
    types: ClassVar[LanguageTypes]
    ops: ClassVar[LanguageOps]


# =====================================================================
# Base expression
# =====================================================================

class VarExpr(GenericArgsMixin, ABC):
    TYPE: ClassVar[str]

    def __init__(self) -> None:
        # First generic type argument is the Language class (for example Make, Kconfig)
        lang_cls: type[Language] = self.get_arg(0)
        self.lang: type[Language] = lang_cls
        self.types: LanguageTypes = lang_cls.types
        self.ops: LanguageOps = lang_cls.ops

    # ---------- unified operator dispatch ----------

    @classmethod
    def _dispatch_binop(
        cls,
        lhs: Any,
        rhs: Any,
        op_cls: Optional[Type["VarBinaryOp"]],
    ) -> "VarExpr":
        # Let Python handle non VarExpr operands (reflected ops etc.)
        if not isinstance(lhs, VarExpr) or not isinstance(rhs, VarExpr):
            return NotImplemented

        lhs._check_same_ops(rhs)
        types = lhs.types

        # Central Null handling for all binary operators
        null_cls = types.Null
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
        null_cls = self.types.Null
        if null_cls is not None and isinstance(self, null_cls):
            return self
        return self.ops.Not(self.simplify()).simplify()

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
        if self.lang is not other.lang:
            raise TypeError("Cannot combine expressions with different Language")

    # ---------- structural API ----------

    @abstractmethod
    def __iter__(self) -> Iterator["VarExpr"]:
        """
        Iterate over structural children of this node.
        Implemented in concrete base node types.
        """
        raise NotImplementedError

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
        if self.lang is not child.lang:
            raise TypeError("Mismatched Language in unary operator")

    def __iter__(self) -> Iterator[VarExpr]:
        yield self.child

    def args(self) -> Tuple[Any, ...]:
        # Structural payload is the child key
        return (self.child.key(),)


class VarBinaryOp(VarExpr):

    def __init__(self, left: VarExpr, right: VarExpr):
        self.left = left
        self.right = right
        super().__init__()
        if self.lang is not left.lang or self.lang is not right.lang:
            raise TypeError("Mismatched Language in binary operator")

    def __iter__(self) -> Iterator[VarExpr]:
        # Right first, then left as you requested earlier
        yield self.right
        yield self.left

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

        lang = terms[0].lang
        for t in terms:
            if t.lang is not lang:
                raise TypeError("Mixed Language in rebuild")

        terms_sorted = sorted(terms, key=lambda e: e.key())
        acc: VarExpr = terms_sorted[0]
        for t in terms_sorted[1:]:
            acc = op_cls(acc, t)  # type: ignore[arg-type]
        return acc


class VarConcrete(VarExpr):
    """
    Base class for leaf nodes or nodes with no structural children.
    """

    def __iter__(self) -> Iterator[VarExpr]:
        return
        yield

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
    No arithmetic here. Use Language.ops.Add/Sub/Mul/Div to enable math or concat.
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
    and dot. Extra allowed characters can be passed with special_chars.
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
    TYPE = "not"

    def simplify(self) -> "VarExpr":
        c = self.child

        if self.types.Bool.isTrue(c):
            return self.types.Bool.false()
        if self.types.Bool.isFalse(c):
            return self.types.Bool.true()

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

        if self.types.Bool.isFalse(left) or self.types.Bool.isFalse(right):
            return self.types.Bool.false()
        if self.types.Bool.isTrue(left):
            return right
        if self.types.Bool.isTrue(right):
            return left
        if left.key() == right.key():
            return left
        if VarBinaryOp.is_negation_pair(left, right):
            return self.types.Bool.false()

        terms = self._flatten_terms(left, right)

        early = self._detect_contradiction(terms)
        if early is not None:
            return early

        terms = self._absorption_with_or(terms)
        terms = self._negated_absorption_with_or(terms)

        return VarBinaryOp.rebuild_sorted(
            terms,
            self.types.Bool.true(),
            self.ops.And,
        )

    def _flatten_terms(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        items: List[VarExpr] = []
        seen = set()

        def add(e: VarExpr) -> None:
            if self.types.Bool.isTrue(e):
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
                return self.types.Bool.false()
            if not isinstance(t, self.ops.Not) and ("not", t.key()) in keys:
                return self.types.Bool.false()
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

        if self.types.Bool.isTrue(left) or self.types.Bool.isTrue(right):
            return self.types.Bool.true()
        if self.types.Bool.isFalse(left):
            return right
        if self.types.Bool.isFalse(right):
            return left
        if left.key() == right.key():
            return left
        if VarBinaryOp.is_negation_pair(left, right):
            return self.types.Bool.true()

        terms = self._flatten_terms(left, right)

        early = self._detect_tautology(terms)
        if early is not None:
            return early

        terms = self._absorption_with_and(terms)
        terms = self._negated_absorption_with_and(terms)

        return VarBinaryOp.rebuild_sorted(
            terms,
            self.types.Bool.false(),
            self.ops.Or,
        )

    def _flatten_terms(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        items: List[VarExpr] = []
        seen = set()

        def add(e: VarExpr) -> None:
            if self.types.Bool.isFalse(e):
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
                return self.types.Bool.true()
            if not isinstance(t, self.ops.Not) and ("not", t.key()) in keys:
                return self.types.Bool.true()
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
# Arithmetic operator classes
# =====================================================================

class VarAdd(VarBinaryOp):
    TYPE = "add"

    def simplify(self) -> VarExpr:
        left = self.left.simplify()
        right = self.right.simplify()

        terms = self._flatten_sum(left, right)
        const_type, const_sum, linear_terms, others = self._collect_linear_terms(terms)
        new_terms = self._rebuild_terms(const_type, const_sum, linear_terms, others)

        if not new_terms:
            # No neutral element type known, keep original
            return self

        if len(new_terms) == 1:
            return new_terms[0]

        add_cls = self.ops.Add or type(self)

        acc: VarExpr = new_terms[0]
        for t in new_terms[1:]:
            acc = add_cls(acc, t)
        return acc

    def _flatten_sum(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        add_cls = type(self)
        items: List[VarExpr] = []

        def walk(e: VarExpr) -> None:
            if isinstance(e, add_cls):
                walk(e.left)
                walk(e.right)
            else:
                items.append(e)

        walk(a)
        walk(b)
        return items

    def _collect_linear_terms(
        self,
        terms: List[VarExpr],
    ) -> Tuple[
        Optional[Type[VarConst]],
        int,
        dict[Tuple[Any, ...], Tuple[int, Optional[Type[VarConst]], VarExpr]],
        List[VarExpr],
    ]:
        const_type: Optional[Type[VarConst]] = None
        const_sum: int = 0

        # base.key() -> (coeff, coeff_type, base_expr)
        linear_terms: dict[Tuple[Any, ...], Tuple[int, Optional[Type[VarConst]], VarExpr]] = {}
        others: List[VarExpr] = []

        for t in terms:
            # Pure integer constant
            if isinstance(t, VarConst) and isinstance(t.value, int):
                t_type = type(t)
                if const_type is None:
                    const_type = t_type
                    const_sum += t.value
                elif t_type is const_type:
                    const_sum += t.value
                else:
                    others.append(t)
                continue

            # Linear term c * base
            if self.ops.Mul is not None and isinstance(t, self.ops.Mul):
                coeff_const, base_expr = self._extract_coeff_base(t)
                if coeff_const is not None and base_expr is not None:
                    base_key = base_expr.key()
                    coeff = coeff_const.value
                    prev = linear_terms.get(base_key)
                    if prev is None:
                        linear_terms[base_key] = (coeff, type(coeff_const), base_expr)
                    else:
                        prev_coeff, prev_type, prev_base = prev
                        if prev_type is type(coeff_const):
                            coeff_type = prev_type
                        elif prev_type is None:
                            coeff_type = type(coeff_const)
                        else:
                            # Mixed coeff types for same base, bail out
                            others.append(t)
                            continue
                        linear_terms[base_key] = (prev_coeff + coeff, coeff_type, prev_base)
                    continue

            # Bare base, coefficient 1
            base_key = t.key()
            prev = linear_terms.get(base_key)
            if prev is None:
                linear_terms[base_key] = (1, None, t)
            else:
                prev_coeff, prev_type, prev_base = prev
                linear_terms[base_key] = (prev_coeff + 1, prev_type, prev_base)

        return const_type, const_sum, linear_terms, others

    def _extract_coeff_base(
        self,
        term: VarExpr,
    ) -> Tuple[Optional[VarConst], Optional[VarExpr]]:
        if self.ops.Mul is None or not isinstance(term, self.ops.Mul):
            return None, None

        l = term.left
        r = term.right

        if isinstance(l, VarConst) and isinstance(l.value, int):
            return l, r
        if isinstance(r, VarConst) and isinstance(r.value, int):
            return r, l

        return None, None

    def _rebuild_terms(
        self,
        const_type: Optional[Type[VarConst]],
        const_sum: int,
        linear_terms: dict[Tuple[Any, ...], Tuple[int, Optional[Type[VarConst]], VarExpr]],
        others: List[VarExpr],
    ) -> List[VarExpr]:
        result: List[VarExpr] = []

        # Constant part
        if const_type is not None and const_sum != 0:
            result.append(const_type(const_sum))  # type: ignore[call-arg]

        # Linear terms
        for _, (coeff, coeff_type, base_expr) in sorted(
            linear_terms.items(), key=lambda item: item[0]
        ):
            if coeff == 0:
                continue

            if coeff_type is not None and self.ops.Mul is not None:
                coeff_const = coeff_type(coeff)  # type: ignore[call-arg]
                result.append(self.ops.Mul(coeff_const, base_expr).simplify())
            else:
                # No stored type, fallback to language Int if available and Mul is available
                if self.types.Int is not None and self.ops.Mul is not None:
                    coeff_const = self.types.Int(coeff)  # type: ignore[call-arg]
                    result.append(self.ops.Mul(coeff_const, base_expr).simplify())
                else:
                    # Last resort: repeat term using Add only
                    if coeff == 1:
                        result.append(base_expr)
                    else:
                        add_cls = self.ops.Add or type(self)
                        acc: VarExpr = base_expr
                        for _ in range(coeff - 1):
                            acc = add_cls(acc, base_expr)
                        result.append(acc.simplify())

        # Others
        result.extend(others)
        return result


class VarSub(VarBinaryOp):
    TYPE = "sub"

    def simplify(self) -> VarExpr:
        left = self.left.simplify()
        right = self.right.simplify()

        # Constant folding for integer constants of same type
        if isinstance(left, VarConst) and isinstance(right, VarConst):
            if (
                isinstance(left.value, int)
                and isinstance(right.value, int)
                and type(left) is type(right)
            ):
                return type(left)(left.value - right.value)  # type: ignore[call-arg]

        # x - 0 => x
        if isinstance(right, VarConst) and isinstance(right.value, int) and right.value == 0:
            return left

        # x - x => 0
        if left.key() == right.key():
            if isinstance(left, VarConst) and isinstance(left.value, int):
                return type(left)(0)  # type: ignore[call-arg]
            if self.types.Int is not None:
                return self.types.Int(0)  # type: ignore[call-arg]
            return self

        # Rewrite x - y as x + (-1) * y so Add can merge
        neg = self._negate_expr(right)
        if neg is not None and self.ops.Add is not None:
            return self.ops.Add(left, neg).simplify()

        return self

    def _negate_expr(self, expr: VarExpr) -> Optional[VarExpr]:
        # Negate integer constant
        if isinstance(expr, VarConst) and isinstance(expr.value, int):
            return type(expr)(-expr.value)  # type: ignore[call-arg]

        # Negate c * base
        if self.ops.Mul is not None and isinstance(expr, self.ops.Mul):
            l = expr.left
            r = expr.right
            if isinstance(l, VarConst) and isinstance(l.value, int):
                return self.ops.Mul(type(l)(-l.value), r).simplify()  # type: ignore[call-arg]
            if isinstance(r, VarConst) and isinstance(r.value, int):
                return self.ops.Mul(l, type(r)(-r.value)).simplify()  # type: ignore[call-arg]

        # Fallback: Int(-1) * expr if available
        if self.types.Int is not None and self.ops.Mul is not None:
            return self.ops.Mul(self.types.Int(-1), expr).simplify()  # type: ignore[call-arg]

        # No safe way to negate
        return None


class VarMul(VarBinaryOp):
    TYPE = "mul"

    def simplify(self) -> VarExpr:
        left = self.left.simplify()
        right = self.right.simplify()

        factors = self._flatten_product(left, right)
        const_type, const_prod, non_const = self._collect_constant_factor(factors)

        # 0 times anything is 0
        if const_type is not None and const_prod == 0:
            return const_type(0)  # type: ignore[call-arg]

        new_factors: List[VarExpr] = []
        if const_type is not None and const_prod != 1:
            new_factors.append(const_type(const_prod))  # type: ignore[call-arg]
        new_factors.extend(non_const)

        if not new_factors:
            if const_type is not None:
                return const_type(const_prod)  # type: ignore[call-arg]
            return self

        if len(new_factors) == 1:
            return new_factors[0]

        mul_cls = self.ops.Mul or type(self)

        acc: VarExpr = new_factors[0]
        for f in new_factors[1:]:
            acc = mul_cls(acc, f)
        return acc

    def _flatten_product(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        # Flatten only this concrete Mul class
        mul_cls = type(self)
        items: List[VarExpr] = []

        def walk(e: VarExpr) -> None:
            if isinstance(e, mul_cls):
                walk(e.left)
                walk(e.right)
            else:
                items.append(e)

        walk(a)
        walk(b)
        return items

    def _collect_constant_factor(
        self,
        factors: List[VarExpr],
    ) -> Tuple[Optional[Type[VarConst]], int, List[VarExpr]]:
        const_type: Optional[Type[VarConst]] = None
        const_prod: int = 1
        non_const: List[VarExpr] = []

        for f in factors:
            if isinstance(f, VarConst) and isinstance(f.value, int):
                t_type = type(f)
                if const_type is None:
                    const_type = t_type
                    const_prod *= f.value
                elif t_type is const_type:
                    const_prod *= f.value
                else:
                    non_const.append(f)
            else:
                non_const.append(f)

        return const_type, const_prod, non_const


class VarDiv(VarBinaryOp):
    TYPE = "div"

    def simplify(self) -> VarExpr:
        left = self.left.simplify()
        right = self.right.simplify()

        # Constant folding for integer constants of same type
        if isinstance(left, VarConst) and isinstance(right, VarConst):
            if (
                isinstance(left.value, int)
                and isinstance(right.value, int)
                and type(left) is type(right)
                and right.value != 0
            ):
                return type(left)(left.value // right.value)  # type: ignore[call-arg]

        # x / 1 => x
        if isinstance(right, VarConst) and isinstance(right.value, int) and right.value == 1:
            return left

        # 0 / x => 0 (for integer zero)
        if isinstance(left, VarConst) and isinstance(left.value, int) and left.value == 0:
            return type(left)(0)  # type: ignore[call-arg]

        # Try to reduce multiplicative constant: (c * base) / d => (c/d) * base
        reduced = self._reduce_constant_factor(left, right)
        if reduced is not None:
            return reduced

        return self

    def _reduce_constant_factor(self, left: VarExpr, right: VarExpr) -> Optional[VarExpr]:
        if not (isinstance(right, VarConst) and isinstance(right.value, int)):
            return None
        if right.value == 0:
            return None

        if self.ops.Mul is None:
            return None

        # Pattern: (c * base) / d
        if isinstance(left, self.ops.Mul):
            l = left.left
            r = left.right
            for const, other in ((l, r), (r, l)):
                if (
                    isinstance(const, VarConst)
                    and isinstance(const.value, int)
                    and type(const) is type(right)
                ):
                    c = const.value
                    d = right.value
                    if c % d == 0:
                        new_c = type(const)(c // d)  # type: ignore[call-arg]
                        return self.ops.Mul(new_c, other).simplify()

        return None
