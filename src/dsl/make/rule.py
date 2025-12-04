from abc import ABC, abstractmethod
from typing import Iterator, Optional, Literal

from dsl.container import NodeBlock
from dsl.content import WordsNode
from dsl.node import nullNode, Node
from dsl.make.core import MElement
from dsl.make.var import MConst, MExpr


class MRule(WordsNode, ABC):
    """
    Header-only Make rule:

      <targets><op> [<prereqs>] [| <order_only>]

    Examples:
      foo: bar baz
      foo:: bar
      a b &: c d | e

    targets, prereqs and order_only are used as-is (no splitting).
    """

    Op = Literal[":", "::", "&:"]

    @property
    @abstractmethod
    def op(self) -> Op:
        raise NotImplementedError

    def __init__(
        self,
        targets: MExpr,
        prereqs: Optional[MExpr] = None,
        order_only: Optional[MExpr] = None,
    ) -> None:
        super().__init__(sep=" ")

        self._targets: MExpr = targets
        self._prereqs: Optional[MExpr] = prereqs
        self._order_only: Optional[MExpr] = order_only

        left = str(targets).strip()
        if not left:
            raise ValueError("Rule requires a non-empty targets expression")

    @property
    def targets(self) -> MExpr:
        return self._targets

    @property
    def prereqs(self) -> Optional[MExpr]:
        return self._prereqs

    @property
    def order_only(self) -> Optional[MExpr]:
        return self._order_only

    def __iter__(self) -> Iterator[str]:
        # First token is "<targets><op>" so we get "foo:" instead of "foo :"
        left = str(self._targets).strip()
        yield f"{left}{self.op}"

        # Optional prerequisites as a single "word" (can contain spaces)
        if self._prereqs is not None:
            right = str(self._prereqs).strip()
            if right:
                yield right

        # Optional order-only part: "| <order_only>"
        if self._order_only is not None:
            oo = str(self._order_only).strip()
            if oo:
                yield "|"
                yield oo


class MStaticRule(MRule):
    """
    Ordinary ':' rule:

      target: prereqs | order_only
    """

    @property
    def op(self) -> MRule.Op:
        return ":"


class MIndependantRule(MRule):
    """
    Double-colon '::' rule:

      target:: prereqs | order_only
    """

    @property
    def op(self) -> MRule.Op:
        return "::"


class MGroupedRule(MRule):
    """
    Grouped '&:' rule:

      t1 t2 &: prereqs | order_only
    """

    @property
    def op(self) -> MRule.Op:
        return "&:"


class MReceipe(NodeBlock[MElement, MRule]):
    """
    Full rule with header and recipe block:

      <MRule header>
        \t<recipe...>

    Example usage:

      header = MSimpleRule(MConst("all"), prereqs=MConst("app"))
      rule = MReceipe(header,
                      TextNode("\t$(MAKE) app"),
                      TextNode("\techo done"))
    """

    def __init__(
        self,
        rule: MRule,
        *commands: MElement,
        margin: Node = nullNode,
        level: int = 1,
    ) -> None:
        super().__init__(rule, *commands, margin=margin, level=level)

class MPhony(MStaticRule):
    def __init__(self, rules:MExpr):
        super().__init__(MConst(".PHONY"),prereqs=rules)
