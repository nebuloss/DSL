# ===== Block constructs: if / menu =====

from abc import ABC, abstractmethod
from dsl.kconfig.lang import KConfig, KElement, KStringKey
from dsl.kconfig.option import KChoiceHeader
from dsl.kconfig.var import KVar
from dsl.lang import Block, Text


class KBlock(Block[KElement,KElement,Text],ABC):
    """
    Helper for simple:

      statement
          <children...>
      end<keyword>
    """
    @classmethod
    @abstractmethod
    def keyword(cls) -> str:
        raise NotImplemented

    def __init__(self, begin: KElement, *children: KElement):
        end = Text(f"end{self.keyword()}")

        super().__init__(
            begin,
            end,
            inner=KConfig.MARGIN,
        )
        self.extend(children)


class KIf(KBlock):
    """
    if CONDITION
        ...
    endif
    """
    @classmethod
    def keyword(cls)->str:
        return "if"

    def __init__(self, condition: KVar, *blocks: KElement):
        super().__init__(Text(f"if {condition}"), *blocks)


class KMenu(KBlock):
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

class KChoice(KBlock):
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
        *choices: KElement,
    ):
        # Main Choice block:
        # begin = header (choice + its properties)
        # children = actual alternatives
        # end = endchoice
        super().__init__(KChoiceHeader(prompt), *choices)
