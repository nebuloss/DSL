# ===== Block constructs: if / menu =====

from abc import abstractmethod,ABC
from dsl.container import DelimitedNodeBlock
from dsl.content import TextNode, WordlistNode
from dsl.kconfig.const import KConstString
from dsl.kconfig.core import KConfig, KElement
from dsl.kconfig.option import KChoiceHeader, KOptionBool
from dsl.kconfig.var import KExpr

class KBlock[TChildK:KElement](DelimitedNodeBlock[TChildK,KElement,TextNode],ABC):
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
        end = TextNode(f"end{self.keyword()}")

        super().__init__(
            begin,
            end,
            margin=KConfig.MARGIN,
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
        super().__init__(WordlistNode(self.keyword,condition), *blocks)


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
        super().__init__(WordlistNode(self.keyword, KConstString(title)), *blocks)


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
