"""
Kconfig top-level nodes.

KConfig  — root container; children are separated by blank lines (same
           pattern as Makefile at the Make layer).
KList    — a plain stack with no extra spacing, for grouping.
KSource  — "source path" line.
KComment — "comment text" line (a Kconfig menu-visible comment entry,
           not a # comment).
"""
from __future__ import annotations

from typing import Optional

from dsl import Node,BlankLineNode,SimpleNodeStack
from dsl.container import NodeStack
from dsl.content import WordlistNode
from dsl.kconfig.var import KString
from dsl.var import VarConst

KElement = Node
KConst=VarConst

class KConfig(NodeStack[KElement]):
    MARGIN:Optional[Node]=BlankLineNode()

    def __init__(self,*elements:KElement):
        super().__init__(*elements,margin=self.MARGIN)

class KList(SimpleNodeStack[KElement]):
    pass

# ===== Simple one-line elements =====

class KSource(WordlistNode):
    """
    Kconfig source line.

    Examples:
      KSource("arch/Kconfig")
    """

    def __init__(self, path: str):
        super().__init__("source", KString(path))

class KComment(WordlistNode):
    def __init__(self, comment: str):
        super().__init__("comment", KString(comment))
