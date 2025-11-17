# ===== Block constructs: if / menu =====

from dsl.kconfig.lang import KConfig, KElement, KStringKey
from dsl.kconfig.option import KChoiceHeader
from dsl.kconfig.var import KVar
from dsl.lang import Block, Node, Text


class KBlock(Block[KElement]):
    """
    Helper for simple:

      statement
          <children...>
      end<keyword>
    """

    def __init__(self, begin: Node, *children: KElement):
        if begin is None:
            raise ValueError("Expecting begin statement")

        words = str(begin).split()
        if not words:
            raise ValueError("Empty begin is not allowed")

        keyword = words[0].lower()
        end = Text(f"end{keyword}")

        super().__init__(
            begin=begin,
            end=end,
            inner=KConfig.MARGIN,
            outer=None
        )
        self.extend(children)


class KIf(KBlock):
    """
    if CONDITION
        ...
    endif
    """

    def __init__(self, condition: KVar, *blocks: KElement):
        super().__init__(Text(f"if {condition}"), *blocks)


class KMenu(KBlock):
    """
    menu "Title"
        ...
    endmenu
    """

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
