from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
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
    Boolean constant.
    Concrete languages define __str__.
    """

    def __init__(self, val: bool):
        self.val = bool(val)
        super().__init__()

    def key(self) -> Tuple[Any, ...]:
        return ("const", self.val)

    def simplify(self) -> "VarExpr[OpsT]":
        return self

    def __len__(self) -> int:
        return 0

    @staticmethod
    def is_true(x: "VarExpr[OpsT]") -> bool:
        return isinstance(x, VarConst) and x.val is True

    @staticmethod
    def is_false(x: "VarExpr[OpsT]") -> bool:
        return isinstance(x, VarConst) and x.val is False


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
        s = name.strip()
        s = s.replace(" ", "_")
        s = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in s)
        if not s:
            raise ValueError("Empty variable name")
        if s[0].isdigit():
            s = "_" + s
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
    PREC = 3  # higher than AND / OR

    def key(self) -> Tuple[Any, ...]:
        return ("not", self.child.key())

    def simplify(self) -> "VarExpr[OpsT]":
        ops = self.ops
        ConstCls: Type[VarConst[OpsT]] = ops.Const  # type: ignore[assignment]
        NotCls: Type["VarNot[OpsT]"] = ops.Not  # type: ignore[assignment]
        AndCls: Type["VarAnd[OpsT]"] = ops.And  # type: ignore[assignment]
        OrCls: Type["VarOr[OpsT]"] = ops.Or  # type: ignore[assignment]

        c = self.child.simplify()

        # !const
        if isinstance(c, ConstCls):
            return ConstCls(not c.val)

        # !!x
        if isinstance(c, NotCls):
            return c.child

        # De Morgan
        if isinstance(c, AndCls):
            return (NotCls(c.left) | NotCls(c.right)).simplify()

        if isinstance(c, OrCls):
            return (NotCls(c.left) & NotCls(c.right)).simplify()

        return NotCls(c)

    def __len__(self) -> int:
        return len(self.child)


# =====================================================================
# AND
# =====================================================================

class VarAnd(VarBinaryOp[OpsT], ABC):
    PREC = 2

    def key(self) -> Tuple[Any, ...]:
        ops = self.ops
        AndCls: Type["VarAnd[OpsT]"] = ops.And  # type: ignore[assignment]
        ConstCls: Type["VarConst[OpsT]"] = ops.Const  # type: ignore[assignment]
        flat = self._flatten_terms(self.left, self.right, AndCls, ConstCls)
        keys = sorted(t.key() for t in flat)
        return ("and", tuple(keys))

    def simplify(self) -> "VarExpr[OpsT]":
        ops = self.ops
        ConstCls: Type["VarConst[OpsT]"] = ops.Const  # type: ignore[assignment]
        NotCls: Type["VarNot[OpsT]"] = ops.Not  # type: ignore[assignment]
        AndCls: Type["VarAnd[OpsT]"] = ops.And  # type: ignore[assignment]
        OrCls: Type["VarOr[OpsT]"] = ops.Or  # type: ignore[assignment]

        L = self.left.simplify()
        R = self.right.simplify()

        # Short circuits
        if isinstance(L, ConstCls):
            if L.val is False:
                return ConstCls(False)
            if L.val is True:
                return R

        if isinstance(R, ConstCls):
            if R.val is False:
                return ConstCls(False)
            if R.val is True:
                return L

        # Idempotent
        if L.key() == R.key():
            return L

        # x && !x
        if VarBinaryOp.is_negation_pair(L, R):
            return ConstCls(False)

        # Flatten nested ANDs, remove True, dedupe
        terms = self._flatten_terms(L, R, AndCls, ConstCls)

        # x && !x among terms
        early = self._detect_contradiction(terms, ConstCls, NotCls)
        if early is not None:
            return early

        # X && (X || Y) -> X
        terms = self._absorption(terms, OrCls)

        # X && (!X || Y) etc
        terms = self._negated_absorption(terms, OrCls, NotCls)

        # Rebuild
        return VarBinaryOp.rebuild_sorted(
            terms,
            ConstCls(True),
            AndCls,
        )

    def __len__(self) -> int:
        return len(self.left) + len(self.right)

    # ----- helpers -----

    @staticmethod
    def _flatten_terms(
        a: VarExpr[OpsT],
        b: VarExpr[OpsT],
        AndCls: Type["VarAnd[OpsT]"],
        ConstCls: Type["VarConst[OpsT]"],
    ) -> List[VarExpr[OpsT]]:
        items: List[VarExpr[OpsT]] = []
        seen = set()

        def add(e: VarExpr[OpsT]) -> None:
            if isinstance(e, ConstCls) and e.val is True:
                return
            k = e.key()
            if k not in seen:
                seen.add(k)
                items.append(e)

        def walk(e: VarExpr[OpsT]) -> None:
            if isinstance(e, AndCls):
                walk(e.left)
                walk(e.right)
            else:
                add(e)

        walk(a)
        walk(b)
        return items

    @staticmethod
    def _detect_contradiction(
        terms: List[VarExpr[OpsT]],
        ConstCls: Type["VarConst[OpsT]"],
        NotCls: Type["VarNot[OpsT]"],
    ) -> Optional[VarExpr[OpsT]]:
        keys = {t.key() for t in terms}
        for t in terms:
            if isinstance(t, NotCls) and t.child.key() in keys:
                return ConstCls(False)
            if not isinstance(t, NotCls) and ("not", t.key()) in keys:
                return ConstCls(False)
        return None

    @staticmethod
    def _absorption(
        terms: List[VarExpr[OpsT]],
        OrCls: Type["VarOr[OpsT]"],
    ) -> List[VarExpr[OpsT]]:
        if not terms:
            return terms
        base = {t.key() for t in terms}
        kept: List[VarExpr[OpsT]] = []
        for t in terms:
            if isinstance(t, OrCls) and (
                t.left.key() in base or t.right.key() in base
            ):
                continue
            kept.append(t)
        return kept

    @staticmethod
    def _negated_absorption(
        terms: List[VarExpr[OpsT]],
        OrCls: Type["VarOr[OpsT]"],
        NotCls: Type["VarNot[OpsT]"],
    ) -> List[VarExpr[OpsT]]:
        if len(terms) <= 1:
            return terms

        base_pos = {t.key() for t in terms if not isinstance(t, NotCls)}
        base_neg = {t.child.key() for t in terms if isinstance(t, NotCls)}

        new_terms: List[VarExpr[OpsT]] = []
        changed = False

        for t in terms:
            if isinstance(t, OrCls):
                l, r = t.left, t.right

                # X && (!X || Y) -> X && Y
                if isinstance(l, NotCls) and l.child.key() in base_pos:
                    new_terms.append(r)
                    changed = True
                    continue
                if isinstance(r, NotCls) and r.child.key() in base_pos:
                    new_terms.append(l)
                    changed = True
                    continue

                # (!X) && (X || Y) -> (!X) && Y
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
# OR
# =====================================================================

class VarOr(VarBinaryOp[OpsT], ABC):
    PREC = 1

    def key(self) -> Tuple[Any, ...]:
        ops = self.ops
        OrCls: Type["VarOr[OpsT]"] = ops.Or  # type: ignore[assignment]
        ConstCls: Type["VarConst[OpsT]"] = ops.Const  # type: ignore[assignment]
        flat = self._flatten_terms(self.left, self.right, OrCls, ConstCls)
        keys = sorted(t.key() for t in flat)
        return ("or", tuple(keys))

    def simplify(self) -> "VarExpr[OpsT]":
        ops = self.ops
        ConstCls: Type["VarConst[OpsT]"] = ops.Const  # type: ignore[assignment]
        NotCls: Type["VarNot[OpsT]"] = ops.Not  # type: ignore[assignment]
        AndCls: Type["VarAnd[OpsT]"] = ops.And  # type: ignore[assignment]
        OrCls: Type["VarOr[OpsT]"] = ops.Or  # type: ignore[assignment]

        L = self.left.simplify()
        R = self.right.simplify()

        # Short circuits
        if isinstance(L, ConstCls):
            if L.val is True:
                return ConstCls(True)
            if L.val is False:
                return R

        if isinstance(R, ConstCls):
            if R.val is True:
                return ConstCls(True)
            if R.val is False:
                return L

        # Idempotent
        if L.key() == R.key():
            return L

        # x || !x
        if VarBinaryOp.is_negation_pair(L, R):
            return ConstCls(True)

        # Flatten nested ORs
        terms = self._flatten_terms(L, R, OrCls, ConstCls)

        # x || !x among terms
        early = self._detect_tautology(terms, ConstCls, NotCls)
        if early is not None:
            return early

        # X || (X && Y) -> X
        terms = self._absorption(terms, AndCls)

        # X || (!X && Y) etc
        terms = self._negated_absorption(terms, AndCls, NotCls)

        # Rebuild
        return VarBinaryOp.rebuild_sorted(
            terms,
            ConstCls(False),
            OrCls,
        )

    def __len__(self) -> int:
        return len(self.left) + len(self.right)

    # ----- helpers -----

    @staticmethod
    def _flatten_terms(
        a: VarExpr[OpsT],
        b: VarExpr[OpsT],
        OrCls: Type["VarOr[OpsT]"],
        ConstCls: Type["VarConst[OpsT]"],
    ) -> List[VarExpr[OpsT]]:
        items: List[VarExpr[OpsT]] = []
        seen = set()

        def add(e: VarExpr[OpsT]) -> None:
            if isinstance(e, ConstCls) and e.val is False:
                return
            k = e.key()
            if k not in seen:
                seen.add(k)
                items.append(e)

        def walk(e: VarExpr[OpsT]) -> None:
            if isinstance(e, OrCls):
                walk(e.left)
                walk(e.right)
            else:
                add(e)

        walk(a)
        walk(b)
        return items

    @staticmethod
    def _detect_tautology(
        terms: List[VarExpr[OpsT]],
        ConstCls: Type["VarConst[OpsT]"],
        NotCls: Type["VarNot[OpsT]"],
    ) -> Optional[VarExpr[OpsT]]:
        keys = {t.key() for t in terms}
        for t in terms:
            if isinstance(t, NotCls) and t.child.key() in keys:
                return ConstCls(True)
            if not isinstance(t, NotCls) and ("not", t.key()) in keys:
                return ConstCls(True)
        return None

    @staticmethod
    def _absorption(
        terms: List[VarExpr[OpsT]],
        AndCls: Type["VarAnd[OpsT]"],
    ) -> List[VarExpr[OpsT]]:
        if not terms:
            return terms
        base = {t.key() for t in terms}
        kept: List[VarExpr[OpsT]] = []
        for t in terms:
            if isinstance(t, AndCls) and (
                t.left.key() in base or t.right.key() in base
            ):
                continue
            kept.append(t)
        return kept

    @staticmethod
    def _negated_absorption(
        terms: List[VarExpr[OpsT]],
        AndCls: Type["VarAnd[OpsT]"],
        NotCls: Type["VarNot[OpsT]"],
    ) -> List[VarExpr[OpsT]]:
        if len(terms) <= 1:
            return terms

        base_pos = {t.key() for t in terms if not isinstance(t, NotCls)}
        base_neg = {t.child.key() for t in terms if isinstance(t, NotCls)}

        new_terms: List[VarExpr[OpsT]] = []
        changed = False

        for t in terms:
            if isinstance(t, AndCls):
                l, r = t.left, t.right

                # X || (!X && Y) -> X || Y
                if isinstance(l, NotCls) and l.child.key() in base_pos:
                    new_terms.append(r)
                    changed = True
                    continue
                if isinstance(r, NotCls) and r.child.key() in base_pos:
                    new_terms.append(l)
                    changed = True
                    continue

                # (!X) || (X && Y) -> (!X) || Y
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
