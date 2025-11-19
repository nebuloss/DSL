# ===== Block constructs: if / menu =====

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from dsl.kconfig.lang import KConfig, KElement, KStringKey
from dsl.kconfig.option import KChoiceHeader, KOptionBool
from dsl.kconfig.var import KExpr
from dsl.lang import Block, Text

TChildK = TypeVar("TChildK", bound=KElement)

class KBlock(Block[TChildK,KElement,Text],Generic[TChildK]):
    """
    Helper for simple:

      statement
          <children...>
      end<keyword>
    """
    @classmethod
    @abstractmethod
    def keyword(cls) -> str:
        raise NotImplementedError


    def __init__(self, begin: KElement, *children: TChildK):
        end = Text(f"end{self.keyword()}")

        super().__init__(
            begin,
            end,
            inner=KConfig.MARGIN,
        )
        self.extend(children)


class KIf(KBlock[KElement]):
    """
    if CONDITION
        ...
    endif
    """
    @classmethod
    def keyword(cls)->str:
        return "if"

    def __init__(self, condition: KExpr, *blocks: KElement):
        super().__init__(Text(f"if {condition}"), *blocks)


class KMenu(KBlock[KElement]):
    """
    menu "Title"
        ...
    endmenu
    """
    @classmethod
    def keyword(cls)->str:
        return "menu"
    
    def __init__(self, title: str, *blocks: KElement):
        super().__init__(KStringKey("menu", title), *blocks)


# ===== Choice: special header block =====

class KChoice(KBlock[KOptionBool]):
    """
    choice
        prompt "..."
        <type_keyword>
        <choices...>
    endchoice

    Properties (prompt, type) are part of the begin block.
    Only the alternatives are children of this Choice node.
    """
    @classmethod
    def keyword(cls)->str:
        return "choice"

    def __init__(
        self,
        prompt: str,
        *choices: KOptionBool,
    ):
        # Main Choice block:
        # begin = header (choice + its properties)
        # children = actual alternatives
        # end = endchoice
        super().__init__(KChoiceHeader(prompt), *choices)
