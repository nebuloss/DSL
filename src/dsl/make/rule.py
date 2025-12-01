# ===== Rules =====

from typing import Any, Dict, Literal, Optional
from dsl.container import NodeBlock
from dsl.content import TextNode
from dsl.make.core import MElement
from dsl.make.var import MConst, MExpr


class MRule(NodeBlock[MElement,TextNode]):
    """
    Builds exactly:

      <targets> <op> <prereqs> [| <order_only>]
        \t<recipe...>

    All inputs are used as-is. No normalization or splitting.
    """

    Op = Literal[":", "::", "&:"]

    def __init__(
        self,
        targets: MExpr,
        *children: MElement,
        prereqs: Optional[MExpr] = None,
        order_only: Optional[MExpr] = None,
        op: Op = ":"
    ):
        if op not in (":", "::", "&:"):
            raise ValueError(f"Invalid rule operator: {op}")

        left = str(targets).strip()
        if not left:
            raise ValueError("Rule requires a non-empty targets string or MExpr")

        right = "" if prereqs is None else str(prereqs).strip()
        oo = "" if order_only is None else str(order_only).strip()

        header = f"{left} {op}"
        if right:
            header += f" {right}"
        if oo:
            header += f" | {oo}"

#        print(f"children={list(children)}")
#        print(f"targets={targets}")
        super().__init__(TextNode(header),*children)
        

class MBuiltinRule(MRule):
    """
    Specialisation of MRule where the targets are fixed at the class level.
    ...
    """

    _builtin_target: Optional[MExpr]=None

    def __init__(
        self,
        *children: MElement,
        prereqs: Optional[MExpr] = None
    ):
        # use the target stored on the class
        if self._builtin_target is None:
            raise TypeError("Builtin target is not set")
        super().__init__(self._builtin_target, *children, prereqs=prereqs)

    def __class_getitem__(cls, target: MExpr):
        """
        MBuiltinRule[".PHONY"] returns a subclass with _builtin_target fixed.
        """
        name = f"{cls.__name__}[{target!s}]"

        namespace: Dict[str, Any] = dict(cls.__dict__)
        namespace["_builtin_target"] = target

        return type(name, (cls,), namespace)

    
MPhonyRule=MBuiltinRule[MConst(".PHONY")]
MDefaultRule=MBuiltinRule[MConst(".DEFAULT")]
MAllRule=MBuiltinRule[MConst("all")]
