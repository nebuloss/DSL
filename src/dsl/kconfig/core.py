#!/usr/bin/env python3
from __future__ import annotations

from typing import Optional

from dsl import Node,BlankLineNode,SimpleNodeStack
from dsl.container import NodeStack
from dsl.content import TextNode, WordlistNode, WordsNode
from dsl.kconfig.const import KConstString

KElement = Node

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
        super().__init__("source", KConstString(path))

class KComment(WordlistNode):
    def __init__(self, comment: str):
        super().__init__("comment", KConstString(comment))
