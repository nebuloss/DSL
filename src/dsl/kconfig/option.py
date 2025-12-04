# ===== Typed options: config / menuconfig =====

from typing import Optional, Union
from dsl.container import NodeBlock
from dsl.content import TextNode, WordAlignedStack, WordlistNode
from dsl.generic_args import GenericArgsMixin
from dsl.kconfig.const import KConst, KConstBool, KConstHex, KConstInt, KConstString
from dsl.kconfig.core import KElement
from dsl.kconfig.var import KExpr, KExpr, KVar

class KOption[ConstT:KConst](GenericArgsMixin,NodeBlock[KElement,TextNode]):
    """
    Generic typed symbol:

      config NAME
          <type_keyword> ["Prompt"]
          [default ...]
          [depends on ...]
    or:
      menuconfig NAME
          <type_keyword> ["Prompt"]
          [default ...]
          [depends on ...]
    """

    def __init__(
        self,
        name: Optional[KVar],
        prompt: Optional[str] = None,
        keyword:str="config",
    ):
        self._name = name
        # Resolve ConstT from generics (like VarExpr does for OpsT)
        const_type:KConst=self.get_arg(0)

        begin_node = WordlistNode(keyword)
        prompt_node=WordlistNode(const_type.typename())

        if name:
            begin_node.append(name)

        if prompt:
            prompt_node.append(KConstString(prompt))
        else:
            prompt_node=WordlistNode(const_type.typename(), KConstString(prompt))

        self._default_list=WordAlignedStack[WordlistNode]()
        self._dependency_list=WordAlignedStack[WordlistNode]()
        self._select_list=WordAlignedStack[WordlistNode]()

        super().__init__(
            begin_node,
            prompt_node,
            self._default_list,
            self._dependency_list,
            self._select_list
        )

    @property
    def name(self) -> KVar:
        return self._name

    # ---------- DSL helpers ----------

    def add_default(
        self,
        value: Union[KVar, ConstT],
        when: KExpr = KConstBool.true(),
    ) -> "KOption[ConstT]":
        """
        Add a 'default' line.

        value:
          - KVar   -> used directly as symbol name
          - ConstT -> must match this option's constant type
        """
        wl=WordlistNode("default",value)
        self._default_list.append(wl)

        if when and not KConstBool.isTrue(when):
            wl.append("if")
            wl.append(when)

        return self

    def add_depends(self, *conds: KExpr) -> "KOption[ConstT]":
        for cond in conds:
            if not KConstBool.isTrue(cond):
                self._dependency_list.append(WordlistNode("depends on",cond))
        return self
    
    def add_selects(self, *vars: KExpr) -> "KOption[ConstT]":
        for var in vars:
            if not KConstBool.isTrue(var):
                self._select_list.append(WordlistNode("select",var))
        return self


# ---------- concrete typed options ----------

class KOptionBool(KOption[KConstBool]):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
    ):
        super().__init__(name, prompt)


class KOptionString(KOption[KConstString]):
    def __init__(self, name: KVar, prompt: Optional[str] = None):
        super().__init__(name, prompt)


class KOptionInt(KOption[KConstInt]):
    def __init__(self, name: KVar, prompt: Optional[str] = None):
        super().__init__(name,prompt)


class KOptionHex(KOption[KConstHex]):
    def __init__(self, name: KVar, prompt: Optional[str] = None):
        super().__init__(name, prompt)


class KMenuConfig(KOption[KConstBool]):
    def __init__(self, name: KVar, prompt: str):
        super().__init__(name,prompt, keyword="menuconfig")

class KChoiceHeader(KOption[KConstBool]):
    def __init__(self, prompt: str):
        super().__init__(None, prompt, keyword="choice")
