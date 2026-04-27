"""
Kconfig block constructs: if, menu, choice.

KBlock uses GenericArgsMixin to bake the keyword into the class:
  KSimpleBlock["if"]   →  renders  "if COND … endif"
  KSimpleBlock["menu"] →  renders  "menu "Title" … endmenu"

The end keyword is derived automatically from the generic argument:
  get_arg(0) == "if"   →  end = TextNode("endif")
  get_arg(0) == "menu" →  end = TextNode("endmenu")

KChoice is special: its header (choice + prompt + bool type) is built from
KChoiceHeader (itself a KOption[KBool] without a name) rather than a simple
keyword, so it inherits the full option builder.
"""
# ===== Block constructs: if / menu =====

from dsl.container import DelimitedNodeBlock
from dsl.content import TextNode, WordlistNode
from dsl.generic_args import GenericArgsMixin
from dsl.kconfig.core import KConfig, KElement
from dsl.kconfig.option import KChoiceHeader, KOptionBool
from dsl.kconfig.var import KExpr,KString

class KBlock(GenericArgsMixin,DelimitedNodeBlock[KElement,KElement,TextNode]):
    """
    Helper for simple:

      statement
          <children...>
      end<keyword>
    """

    def __init__(self, begin: KElement, *children: KElement):
        end = TextNode(f"end{self.get_arg(0)}")

        super().__init__(
            begin,
            end,
            margin=KConfig.MARGIN,
        )
        self.extend(children)

class KSimpleBlock(KBlock):
    def __init__(self, arg: KExpr, *items:KElement):
        super().__init__(WordlistNode(self.get_arg(0),arg), *items)

class KIf(KSimpleBlock["if"]):
    """
    if CONDITION
        ...
    endif
    """
    def __init__(self, condition: KExpr, *items: KElement):
        super().__init__(condition, *items)


class KMenu(KSimpleBlock["menu"]):
    """
    menu "Title"
        ...
    endmenu
    """    
    def __init__(self, title:str, *items: KElement):
        super().__init__(KString(title), *items)


# ===== Choice: special header block =====

class KChoice(KBlock["choice"]):
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
        *choices: KOptionBool,
    ):
        # Main Choice block:
        # begin = header (choice + its properties)
        # children = actual alternatives
        # end = endchoice
        super().__init__(KChoiceHeader(prompt), *choices)
