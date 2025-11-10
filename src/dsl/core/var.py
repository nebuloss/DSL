from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from typing import (
    Any,
    ClassVar,
    Generic,
    List,
    Optional,
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
    Per-language class table.

    Concrete languages:

        class KconfigOps(LanguageOps):
            pass

        class KConst(VarConst[KconfigOps]): ...
        class KVar(VarName[KconfigOps]): ...
        class KNot(VarNot[KconfigOps]): ...
        class KAnd(VarAnd[KconfigOps]): ...
        class KOr(VarOr[KconfigOps]): ...

        KconfigOps.Const = KConst
        KconfigOps.Name  = KVar
        KconfigOps.Not   = KNot
        KconfigOps.And   = KAnd
        KconfigOps.Or    = KOr

    We use the LanguageOps *subclass* as the ops table. Node instances
    store `self.ops = ThatOpsClass`.
    """

    Const: Type["VarConst"]
    Name: Type["VarName"]
    Not: Type["VarNot"]
    And: Type["VarAnd"]
    Or: Type["VarOr"]


OpsT = TypeVar("OpsT", bound=LanguageOps)


# =====================================================================
# Base expression
# =====================================================================

class VarExpr(Generic[OpsT], ABC):
    """
    Generic boolean expression.

    Each instance:
      - infers its `self.ops` from its generic parameter, using the same
        pattern as your Container `_resolve_child_type`.
      - `self.ops` is a LanguageOps subclass (e.g. KconfigOps).

    No global mutable state.
    No class-level OPS in the core.
    """

    def __init__(self):
        self.ops: Type[LanguageOps] = self._resolve_ops()

    # ---------- resolve LanguageOps from generics ----------

    def _resolve_ops(self) -> Type[LanguageOps]:
        # 1) Instance-level generic info (rare, but check)
        orig = getattr(self, "__orig_class__", None)
        if orig is not None:
            args = get_args(orig)
            if args:
                cand = args[0]
                if self._is_valid_ops(cand):
                    return cand

        # 2) Class-level bases: e.g. KConst(VarConst[KconfigOps])
        for base in getattr(type(self), "__orig_bases__", ()):
            args = get_args(base)
            if args:
                cand = args[0]
                if self._is_valid_ops(cand):
                    return cand

        raise TypeError(
            f"Could not resolve LanguageOps for {type(self).__name__}. "
            "Declare your node as VarExpr[YourOps] / VarConst[YourOps] / etc, "
            "and set YourOps.Const/Name/Not/And/Or to the concrete classes."
        )

    @staticmethod
    def _is_valid_ops(cand: Any) -> bool:
        if not isinstance(cand, type):
            return False
        if not issubclass(cand, LanguageOps):
            return False

        # Check that all required fields are defined on this LanguageOps class
        required = ("Const", "Name", "Not", "And", "Or")
        for attr in required:
            if getattr(cand, attr, None) is None:
                # Either missing or explicitly None
                return False
        return True

    # ---------- language consistency ----------

    def _check_same_ops(self, other: "VarExpr") -> None:
        if self.ops is not other.ops:
            raise TypeError("Cannot combine expressions with different LanguageOps")

    # ---------- boolean operators ----------

    def __or__(self, other: "VarExpr") -> "VarExpr":
        self._check_same_ops(other)
        OrCls: Type[VarOr] = self.ops.Or  # type: ignore[assignment]
        return OrCls(self, other).simplify()

    def __and__(self, other: "VarExpr") -> "VarExpr":
        self._check_same_ops(other)
        AndCls: Type[VarAnd] = self.ops.And  # type: ignore[assignment]
        return AndCls(self, other).simplify()

    def __invert__(self) -> "VarExpr":
        NotCls: Type[VarNot] = self.ops.Not  # type: ignore[assignment]
        return NotCls(self).simplify()

    # ---------- structural API ----------

    @abstractmethod
    def key(self) -> Tuple[Any, ...]:
        """
        Structural identity for simplification and ordering.
        """

    @abstractmethod
    def simplify(self) -> "VarExpr":
        """
        Return a logically equivalent, possibly simplified expression.
        """

    @abstractmethod
    def __len__(self) -> int:
        """
        Size / complexity measure.
        """

    # ---------- printing ----------

    @abstractmethod
    def __str__(self) -> str:
        """
        No default textual form.
        Each language specific subclass implements this.
        """
        ...


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
    def rebuild_sorted(
        terms: List["VarExpr[OpsT]"],
        empty_val: "VarExpr[OpsT]",
        op_cls: Type["VarBinaryOp[OpsT]"],
    ) -> "VarExpr[OpsT]":
        """
        Deterministically rebuild a left-associated tree from terms.
        All terms must share the same ops as empty_val.
        """
        if not terms:
            return empty_val
        if len(terms) == 1:
            return terms[0]

        ops = terms[0].ops
        for t in terms:
            if t.ops is not ops:
                raise TypeError("Mixed LanguageOps in rebuild_sorted")

        terms_sorted = sorted(terms, key=lambda e: e.key())
        acc: VarExpr[OpsT] = terms_sorted[0]
        for t in terms_sorted[1:]:
            acc = op_cls(acc, t)  # type: ignore[arg-type]
        return acc

    @staticmethod
    def is_negation_pair(a: "VarExpr[OpsT]", b: "VarExpr[OpsT]") -> bool:
        ak = a.key()
        bk = b.key()
        return ak == ("not", bk) or bk == ("not", ak)


# =====================================================================
# Leaves
# =====================================================================

class VarConst(VarExpr[OpsT], ABC):
    """
    Constant node.
    Now accepts any Python value. Boolean logic in the simplifiers still
    triggers only when val is exactly True or exactly False.
    Concrete languages define __str__.
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
    def isTrue(cls,x: "VarExpr[OpsT]") -> bool:
        return isinstance(x, cls) and x.val is True

    @classmethod
    def isFalse(cls,x: "VarExpr[OpsT]") -> bool:
        return isinstance(x, cls) and x.val is False

    @classmethod
    def true(cls) -> "VarConst[OpsT]":
        return cls(True)  # type: ignore[call-arg]

    @classmethod
    def false(cls) -> "VarConst[OpsT]":
        return cls(False)  # type: ignore[call-arg]

class VarName(VarExpr[OpsT], ABC):
    """
    Normalized variable name with generic rules.

    Input: str only (languages can override normalize).
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

        # Replace spaces, tabs, and hyphens with underscores
        s = re.sub(r"[ \t-]+", "_", s)

        # Validate: must start with a letter or underscore, and only contain alphanumerics or underscores
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s):
            raise ValueError(f"Illegal variable name: {name!r}")

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


# =====================================================================
# NOT
# =====================================================================

class VarNot(VarUnaryOp[OpsT], ABC):
    PREC = 3

    def key(self) -> Tuple[Any, ...]:
        return ("not", self.child.key())

    def simplify(self) -> "VarExpr[OpsT]":
        c = self.child.simplify()

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



# =====================================================================
# AND
# =====================================================================

class VarAnd(VarBinaryOp[OpsT], ABC):
    PREC = 2

    def key(self) -> Tuple[Any, ...]:
        flat = self._flatten_terms(self.left, self.right)
        keys = sorted(t.key() for t in flat)
        return ("and", tuple(keys))

    def simplify(self) -> "VarExpr[OpsT]":
        left = self.left.simplify()
        right = self.right.simplify()

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


# =====================================================================
# OR
# =====================================================================

class VarOr(VarBinaryOp[OpsT], ABC):
    PREC = 1

    def key(self) -> Tuple[Any, ...]:
        flat = self._flatten_terms(self.left, self.right)
        keys = sorted(t.key() for t in flat)
        return ("or", tuple(keys))

    def simplify(self) -> "VarExpr[OpsT]":
        left = self.left.simplify()
        right = self.right.simplify()

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

