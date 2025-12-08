from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from typing import Any, ClassVar, Iterator, List, Optional, Self, Tuple, Type

from dsl.generic_args import GenericArgsMixin


# =====================================================================
# Language descriptor
# =====================================================================

@dataclass
class LanguageTypes:
    Bool: Optional[Type["VarBool"]] = None
    Name: Optional[Type["VarName"]] = None

    Null: Optional[Type["VarNull"]] = None
    Int: Optional[Type["VarInt"]] = None
    String: Optional[Type["VarString"]] = None


@dataclass
class LanguageOps:
    Not: Optional[Type["VarNot"]] = None
    And: Optional[Type["VarAnd"]] = None
    Or: Optional[Type["VarOr"]] = None

    Add: Optional[Type["VarAdd"]] = None
    Sub: Optional[Type["VarSub"]] = None
    Mul: Optional[Type["VarMul"]] = None
    Div: Optional[Type["VarDiv"]] = None


class Language:
    def __init__(self, name: str | None = None) -> None:
        self.name = name or "Language"
        self.types = LanguageTypes()
        self.ops = LanguageOps()

    def validate(self) -> None:
        missing: list[str] = []
        if self.types.Bool is None:
            missing.append("types.Bool")
        if self.types.Name is None:
            missing.append("types.Name")
        if self.ops.Not is None:
            missing.append("ops.Not")
        if self.ops.And is None:
            missing.append("ops.And")
        if self.ops.Or is None:
            missing.append("ops.Or")
        if missing:
            raise RuntimeError(
                f"Language {self.name} missing descriptors: {', '.join(missing)}"
            )


# =====================================================================
# Base expression
# =====================================================================

class VarExpr(GenericArgsMixin, ABC):
    # Bound Language instance per concrete class
    LANGUAGE: ClassVar[Language]

    # ---------- language resolver ----------

    @classmethod
    def resolve_language(cls) -> Language:
        """Return the Language instance bound to this Var class."""
        lang = getattr(cls, "LANGUAGE", None)
        if isinstance(lang, Language):
            return lang

        # First generic argument is mandatory for language bound classes
        candidate = cls.get_arg(0)
        if not isinstance(candidate, Language):
            raise TypeError(
                f"First generic argument of {cls.__name__} must be a Language instance, "
                f"got {candidate!r}"
            )
        cls.LANGUAGE = candidate
        return candidate

    def __init__(self) -> None:
        # Check and use the class level LANGUAGE
        lang = type(self).resolve_language()
        self.types: LanguageTypes = lang.types
        self.ops: LanguageOps = lang.ops

    # ---------- unified operator dispatch ----------

    @classmethod
    def _dispatch_binop(
        cls,
        lhs: Any,
        rhs: Any,
        op_cls: Optional[Type["VarBinaryOp"]],
    ) -> "VarExpr":
        if not isinstance(lhs, VarExpr) or not isinstance(rhs, VarExpr):
            return NotImplemented

        lhs._check_same_ops(rhs)
        types = lhs.types

        # Central Null handling for all binary operators
        null_cls = types.Null
        if null_cls is not None:
            lhs_is_null = isinstance(lhs, VarNull)
            rhs_is_null = isinstance(rhs, VarNull)

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

    # Boolean logic
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
        null_cls = self.types.Null
        if null_cls is not None and isinstance(self, VarNull):
            return self

        not_cls = self.ops.Not
        if not_cls is None:
            raise TypeError("This language does not define logical NOT")

        return not_cls(self.simplify()).simplify()

    # Arithmetic / concat
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
        if type(self).resolve_language() is not type(other).resolve_language():
            raise TypeError("Cannot combine expressions with different Language instances")

    # ---------- structural API ----------

    @abstractmethod
    def __iter__(self) -> Iterator["VarExpr"]:
        raise NotImplementedError

    @abstractmethod
    def args(self) -> Tuple[Any, ...]:
        raise NotImplementedError

    def key(self) -> Tuple[Any, ...]:
        return (self.TYPE, *self.args())  # type: ignore[attr-defined]

    @abstractmethod
    def simplify(self) -> "VarExpr":
        raise NotImplementedError

    def __len__(self) -> int:
        return 1 + sum(len(child) for child in self)

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        return isinstance(other, VarExpr) and self.key() == other.key()


# =====================================================================
# Unary / Binary bases
# =====================================================================

class VarUnaryOp(VarExpr):
    def __init__(self, child: VarExpr):
        self.child = child
        super().__init__()
        if type(self).resolve_language() is not type(child).resolve_language():
            raise TypeError("Mismatched Language in unary operator")

    def __iter__(self) -> Iterator[VarExpr]:
        yield self.child

    def args(self) -> Tuple[Any, ...]:
        return (self.child.key(),)


class VarBinaryOp(VarExpr):
    def __init__(self, left: VarExpr, right: VarExpr):
        self.left = left
        self.right = right
        super().__init__()
        if type(self).resolve_language() is not type(left).resolve_language() \
           or type(self).resolve_language() is not type(right).resolve_language():
            raise TypeError("Mismatched Language in binary operator")

    def __iter__(self) -> Iterator[VarExpr]:
        yield self.right
        yield self.left

    def args(self) -> Tuple[Any, ...]:
        return (self.left.key(), self.right.key())

    @staticmethod
    def is_negation_pair(a: "VarExpr", b: "VarExpr") -> bool:
        ak = a.key()
        bk = b.key()
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

        lang = type(terms[0]).resolve_language()
        for t in terms:
            if type(t).resolve_language() is not lang:
                raise TypeError("Mixed Language in rebuild")

        terms_sorted = sorted(terms, key=lambda e: e.key())
        acc: VarExpr = terms_sorted[0]
        for t in terms_sorted[1:]:
            acc = op_cls(acc, t)  # type: ignore[arg-type]
        return acc


# =====================================================================
# Concrete base
# =====================================================================

class VarConcrete(VarExpr):
    # Default declaration point for TYPE
    TYPE: ClassVar[str]

    def __iter__(self) -> Iterator[VarExpr]:
        if False:
            yield None  # type: ignore[misc]

    def simplify(self) -> Self:
        return self

    def args(self) -> Tuple[Any, ...]:
        return ()


# =====================================================================
# Leaves
# =====================================================================

class VarConst(VarConcrete):
    def __init__(self, val: Any):
        self._val = val
        super().__init__()

    @property
    def value(self):
        return self._val

    def args(self) -> Tuple[Any, ...]:
        return (self._val,)


class VarBool(VarConst):
    TYPE = "bool"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Skip base
        if cls is VarBool:
            return
        lang = cls.resolve_language()
        lang.types.Bool = cls  # type: ignore[assignment]

    def __init__(self, val):
        super().__init__(bool(val))

    @classmethod
    def isTrue(cls, x: "VarExpr") -> bool:
        return isinstance(x, cls) and x.value is True

    @classmethod
    def isFalse(cls, x: "VarExpr") -> bool:
        return isinstance(x, cls) and x.value is False

    @classmethod
    def true(cls) -> Self:
        return cls(True)  # type: ignore[call-arg]

    @classmethod
    def false(cls) -> Self:
        return cls(False)  # type: ignore[call-arg]


class VarString(VarConst):
    TYPE = "string"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarString:
            return
        lang = cls.resolve_language()
        lang.types.String = cls  # type: ignore[assignment]

    def __init__(self, val):
        super().__init__(str(val))


class VarInt(VarConst):
    TYPE = "int"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarInt:
            return
        lang = cls.resolve_language()
        lang.types.Int = cls  # type: ignore[assignment]

    def __init__(self, val):
        super().__init__(int(val))


class VarName(VarConcrete):
    TYPE = "name"

    # Base allowed characters: letters, digits, underscore, dot
    _BASE_ALLOWED = "A-Za-z0-9_."
    _ILLEGAL_CHAR_RE = re.compile(rf"[^{_BASE_ALLOWED}]")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarName:
            return
        lang = cls.resolve_language()
        lang.types.Name = cls  # type: ignore[assignment]

    def __init__(self, name: str, special_chars: str = ""):
        if not isinstance(name, str):
            raise TypeError("Variable name must be a string")

        s = name.strip()
        if not s:
            raise ValueError("Empty variable name")

        # Replace spaces with underscore
        s = s.replace(" ", "_")

        # Build a regex that treats special_chars as extra allowed characters
        if special_chars:
            extra = re.escape(special_chars)
            klass = type(self)
            illegal_re = re.compile(rf"[^{klass._BASE_ALLOWED}{extra}]")
        else:
            illegal_re = type(self)._ILLEGAL_CHAR_RE

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
        return (self._name,)

    def add_prefix(self, prefix: str) -> Self:
        return type(self)(f"{prefix}_{self.name}")

    def add_suffix(self, suffix: str) -> Self:
        return type(self)(f"{self.name}_{suffix}")


class VarNull(VarConcrete):
    TYPE = "null"

    _instance: Optional["VarNull"] = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarNull:
            return
        lang = cls.resolve_language()
        lang.types.Null = cls  # type: ignore[assignment]

    def __new__(cls) -> "VarNull":
        if cls is VarNull:
            raise TypeError("VarNull must be subclassed per language")
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def args(self) -> Tuple[Any, ...]:
        return ()

    @classmethod
    def isNull(cls, expr: "VarExpr") -> bool:
        return isinstance(expr, cls)


# =====================================================================
# Logic
# =====================================================================

class VarNot(VarUnaryOp):
    TYPE = "not"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarNot:
            return
        lang = cls.resolve_language()
        lang.ops.Not = cls  # type: ignore[assignment]

    def simplify(self) -> "VarExpr":
        c = self.child
        bool_type = self.types.Bool

        if bool_type is not None:
            if bool_type.isTrue(c):
                return bool_type.false()
            if bool_type.isFalse(c):
                return bool_type.true()

        if isinstance(c, VarNot):
            # ~~X => X
            return c.child

        if isinstance(c, VarAnd):
            # De Morgan
            return (self.ops.Not(c.left) | self.ops.Not(c.right)).simplify()  # type: ignore[call-arg]

        if isinstance(c, VarOr):
            # De Morgan
            return (self.ops.Not(c.left) & self.ops.Not(c.right)).simplify()  # type: ignore[call-arg]

        # Nothing more to do structurally
        return self.ops.Not(c)  # type: ignore[call-arg]


class VarAnd(VarBinaryOp):
    TYPE = "and"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarAnd:
            return
        lang = cls.resolve_language()
        lang.ops.And = cls  # type: ignore[assignment]

    def simplify(self) -> "VarExpr":
        left = self.left
        right = self.right
        bool_type = self.types.Bool

        if bool_type is not None:
            if bool_type.isFalse(left) or bool_type.isFalse(right):
                return bool_type.false()
            if bool_type.isTrue(left):
                return right
            if bool_type.isTrue(right):
                return left

        if left.key() == right.key():
            return left
        if VarBinaryOp.is_negation_pair(left, right):
            if bool_type is not None:
                return bool_type.false()

        terms = self._flatten_terms(left, right)

        early = self._detect_contradiction(terms)
        if early is not None:
            return early

        terms = self._absorption_with_or(terms)
        terms = self._negated_absorption_with_or(terms)

        if bool_type is None:
            and_cls = self.ops.And or type(self)
            return VarBinaryOp.rebuild_sorted(terms, self, and_cls)  # type: ignore[arg-type]

        return VarBinaryOp.rebuild_sorted(
            terms,
            bool_type.true(),
            self.ops.And or type(self),  # type: ignore[arg-type]
        )

    def _flatten_terms(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        items: List[VarExpr] = []
        seen = set()

        def add(e: VarExpr) -> None:
            bt = self.types.Bool
            if bt is not None and bt.isTrue(e):
                return
            k = e.key()
            if k not in seen:
                seen.add(k)
                items.append(e)

        def walk(e: VarExpr) -> None:
            if isinstance(e, VarAnd):
                walk(e.left)
                walk(e.right)
            else:
                add(e)

        walk(a)
        walk(b)
        return items

    def _detect_contradiction(self, terms: List[VarExpr]) -> Optional[VarExpr]:
        bool_type = self.types.Bool
        if bool_type is None:
            return None

        keys = {t.key() for t in terms}
        for t in terms:
            if isinstance(t, VarNot) and t.child.key() in keys:
                return bool_type.false()
            if not isinstance(t, VarNot) and ("not", t.key()) in keys:
                return bool_type.false()
        return None

    def _absorption_with_or(self, terms: List[VarExpr]) -> List[VarExpr]:
        if not terms:
            return terms
        base = {t.key() for t in terms}
        kept: List[VarExpr] = []
        for t in terms:
            if isinstance(t, VarOr) and (t.left.key() in base or t.right.key() in base):
                continue
            kept.append(t)
        return kept

    def _negated_absorption_with_or(self, terms: List[VarExpr]) -> List[VarExpr]:
        if len(terms) <= 1:
            return terms

        base_pos = {t.key() for t in terms if not isinstance(t, VarNot)}
        base_neg = {t.child.key() for t in terms if isinstance(t, VarNot)}

        new_terms: List[VarExpr] = []
        changed = False

        for t in terms:
            if isinstance(t, VarOr):
                l, r = t.left, t.right

                if isinstance(l, VarNot) and l.child.key() in base_pos:
                    new_terms.append(r)
                    changed = True
                    continue
                if isinstance(r, VarNot) and r.child.key() in base_pos:
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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarOr:
            return
        lang = cls.resolve_language()
        lang.ops.Or = cls  # type: ignore[assignment]

    def simplify(self) -> "VarExpr":
        left = self.left
        right = self.right
        bool_type = self.types.Bool

        if bool_type is not None:
            if bool_type.isTrue(left) or bool_type.isTrue(right):
                return bool_type.true()
            if bool_type.isFalse(left):
                return right
            if bool_type.isFalse(right):
                return left

        if left.key() == right.key():
            return left
        if VarBinaryOp.is_negation_pair(left, right):
            if bool_type is not None:
                return bool_type.true()

        terms = self._flatten_terms(left, right)

        early = self._detect_tautology(terms)
        if early is not None:
            return early

        terms = self._absorption_with_and(terms)
        terms = self._negated_absorption_with_and(terms)

        if bool_type is None:
            or_cls = self.ops.Or or type(self)
            return VarBinaryOp.rebuild_sorted(terms, self, or_cls)  # type: ignore[arg-type]

        return VarBinaryOp.rebuild_sorted(
            terms,
            bool_type.false(),
            self.ops.Or or type(self),  # type: ignore[arg-type]
        )

    def _flatten_terms(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        items: List[VarExpr] = []
        seen = set()

        def add(e: VarExpr) -> None:
            bt = self.types.Bool
            if bt is not None and bt.isFalse(e):
                return
            k = e.key()
            if k not in seen:
                seen.add(k)
                items.append(e)

        def walk(e: VarExpr) -> None:
            if isinstance(e, VarOr):
                walk(e.left)
                walk(e.right)
            else:
                add(e)

        walk(a)
        walk(b)
        return items

    def _detect_tautology(self, terms: List[VarExpr]) -> Optional[VarExpr]:
        bool_type = self.types.Bool
        if bool_type is None:
            return None

        keys = {t.key() for t in terms}
        for t in terms:
            if isinstance(t, VarNot) and t.child.key() in keys:
                return bool_type.true()
            if not isinstance(t, VarNot) and ("not", t.key()) in keys:
                return bool_type.true()
        return None

    def _absorption_with_and(self, terms: List[VarExpr]) -> List[VarExpr]:
        if not terms:
            return terms
        base = {t.key() for t in terms}
        kept: List[VarExpr] = []
        for t in terms:
            if isinstance(t, VarAnd) and (t.left.key() in base or t.right.key() in base):
                continue
            kept.append(t)
        return kept

    def _negated_absorption_with_and(self, terms: List[VarExpr]) -> List[VarExpr]:
        if len(terms) <= 1:
            return terms

        base_pos = {t.key() for t in terms if not isinstance(t, VarNot)}
        base_neg = {t.child.key() for t in terms if isinstance(t, VarNot)}

        new_terms: List[VarExpr] = []
        changed = False

        for t in terms:
            if isinstance(t, VarAnd):
                l, r = t.left, t.right

                if isinstance(l, VarNot) and l.child.key() in base_pos:
                    new_terms.append(r)
                    changed = True
                    continue
                if isinstance(r, VarNot) and r.child.key() in base_pos:
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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarAdd:
            return
        lang = cls.resolve_language()
        lang.ops.Add = cls  # type: ignore[assignment]

    def simplify(self) -> VarExpr:
        left = self.left.simplify()
        right = self.right.simplify()

        terms = self._flatten_sum(left, right)
        const_type, const_sum, linear_terms, others = self._collect_linear_terms(terms)
        new_terms = self._rebuild_terms(const_type, const_sum, linear_terms, others)

        if not new_terms:
            return self

        if len(new_terms) == 1:
            return new_terms[0]

        add_cls = self.ops.Add or type(self)

        acc: VarExpr = new_terms[0]
        for t in new_terms[1:]:
            acc = add_cls(acc, t)
        return acc

    def _flatten_sum(self, a: VarExpr, b: VarExpr) -> List[VarExpr]:
        items: List[VarExpr] = []

        def walk(e: VarExpr) -> None:
            if isinstance(e, VarAdd):
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
            # pure integer constant
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

            # linear term c * base
            if isinstance(t, VarMul):
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
                            # mixed coeff types, give up on this term
                            others.append(t)
                            continue
                        linear_terms[base_key] = (prev_coeff + coeff, coeff_type, prev_base)
                    continue

            # bare base, coefficient 1
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
        if not isinstance(term, VarMul):
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

        add_cls = self.ops.Add or type(self)
        mul_cls = self.ops.Mul  # may be None

        # constant part
        if const_type is not None and const_sum != 0:
            result.append(const_type(const_sum))  # type: ignore[call-arg]

        # linear terms
        for _, (coeff, coeff_type, base_expr) in sorted(
            linear_terms.items(), key=lambda item: item[0]
        ):
            if coeff == 0:
                continue

            if coeff_type is not None and mul_cls is not None:
                coeff_const = coeff_type(coeff)  # type: ignore[call-arg]
                result.append(mul_cls(coeff_const, base_expr).simplify())
            elif coeff_type is None and self.types.Int is not None and mul_cls is not None:
                coeff_const = self.types.Int(coeff)  # type: ignore[call-arg]
                result.append(mul_cls(coeff_const, base_expr).simplify())
            else:
                # cannot create a Mul node safely, fallback to repeated Add
                if coeff == 1:
                    result.append(base_expr)
                else:
                    acc: VarExpr = base_expr
                    for _ in range(coeff - 1):
                        acc = add_cls(acc, base_expr)
                    result.append(acc.simplify())

        # others stay as they are
        result.extend(others)
        return result


class VarSub(VarBinaryOp):
    TYPE = "sub"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarSub:
            return
        lang = cls.resolve_language()
        lang.ops.Sub = cls  # type: ignore[assignment]

    def simplify(self) -> VarExpr:
        left = self.left.simplify()
        right = self.right.simplify()

        # constant folding for integer constants
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

        # rewrite x - y as x + (-1) * y
        neg = self._negate_expr(right)
        if neg is not None:
            add_cls = self.ops.Add or VarAdd
            return add_cls(left, neg).simplify()

        return self

    def _negate_expr(self, expr: VarExpr) -> Optional[VarExpr]:
        # negate integer constant
        if isinstance(expr, VarConst) and isinstance(expr.value, int):
            return type(expr)(-expr.value)  # type: ignore[call-arg]

        mul_cls = self.ops.Mul

        # negate c * base
        if isinstance(expr, VarMul) and mul_cls is not None:
            l = expr.left
            r = expr.right
            if isinstance(l, VarConst) and isinstance(l.value, int):
                return mul_cls(type(l)(-l.value), r).simplify()  # type: ignore[call-arg]
            if isinstance(r, VarConst) and isinstance(r.value, int):
                return mul_cls(l, type(r)(-r.value)).simplify()  # type: ignore[call-arg]

        # fallback Int(-1) * expr
        if self.types.Int is not None and mul_cls is not None:
            return mul_cls(self.types.Int(-1), expr).simplify()  # type: ignore[call-arg]

        return None


class VarMul(VarBinaryOp):
    TYPE = "mul"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarMul:
            return
        lang = cls.resolve_language()
        lang.ops.Mul = cls  # type: ignore[assignment]

    def simplify(self) -> VarExpr:
        left = self.left.simplify()
        right = self.right.simplify()

        factors = self._flatten_product(left, right)
        const_type, const_prod, non_const = self._collect_constant_factor(factors)

        # 0 * anything => 0
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
        items: List[VarExpr] = []

        def walk(e: VarExpr) -> None:
            if isinstance(e, VarMul):
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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is VarDiv:
            return
        lang = cls.resolve_language()
        lang.ops.Div = cls  # type: ignore[assignment]

    def simplify(self) -> VarExpr:
        left = self.left.simplify()
        right = self.right.simplify()

        # constant folding
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

        # 0 / x => 0
        if isinstance(left, VarConst) and isinstance(left.value, int) and left.value == 0:
            return type(left)(0)  # type: ignore[call-arg]

        # (c * base) / d => (c/d) * base when divisible
        reduced = self._reduce_constant_factor(left, right)
        if reduced is not None:
            return reduced

        return self

    def _reduce_constant_factor(self, left: VarExpr, right: VarExpr) -> Optional[VarExpr]:
        if not isinstance(right, VarConst) or not isinstance(right.value, int):
            return None
        if right.value == 0:
            return None

        if not isinstance(left, VarMul):
            return None

        mul_cls = type(left)

        l = left.left
        r = left.right

        for const, other in ((l, r), (r, l)):
            if (
                isinstance(const, VarConst)
                and isinstance(const.value, int)
                and type(const) is type(right)
            ):
                q, rem = divmod(const.value, right.value)
                if rem == 0:
                    new_c = type(const)(q)  # type: ignore[call-arg]
                    return mul_cls(new_c, other).simplify()

        return None
