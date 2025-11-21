#!/usr/bin/env python3
from __future__ import annotations

from typing import Optional

from dsl import Node,Text,Stack,BlankLine,SimpleNodeStack

KElement = Node

class KConfig(Stack[KElement]):
    MARGIN:Optional[Node]=BlankLine()

    def __init__(self,*elements:KElement):
        super().__init__(*elements,inner=self.MARGIN)

class KList(SimpleNodeStack[KElement]):
    pass

class KStringKey(Text):
    """
    Render: <keyword> "<escaped value>"

    Examples:
      prompt "My feature"
      menu "Main menu"
      comment "Something"
      source "path/Kconfig"
    """

    @staticmethod
    def escape(s: str) -> str:
        return s.replace('"', r'\"')

    def __init__(self, keyword: str, value: str):
        if not isinstance(value,str):
            raise TypeError("Expecting string value")
        
        super().__init__(f'{keyword} "{self.escape(value)}"')

# ===== Simple one-line elements =====

class KSource(KStringKey):
    """
    Kconfig source line.

    Examples:
      KSource("arch/Kconfig")
    """

    def __init__(self, path: str):
        super().__init__("source", path)

class KComment(KStringKey):
    def __init__(self, comment: str):
        super().__init__("comment", comment)
