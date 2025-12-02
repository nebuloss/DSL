# ===== Rules =====

from typing import Literal, Optional
from dsl.container import NodeBlock
from dsl.content import TextNode
from dsl.make.core import MElement
from dsl.make.var import MExpr


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
        


