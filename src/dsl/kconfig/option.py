# ===== Typed options: config / menuconfig =====

from typing import Optional, Union
from dsl.container import NodeBlock, WordAlignedStack
from dsl.content import TextNode
from dsl.generic_args import GenericArgsMixin
from dsl.kconfig.const import KConstBool, KConstHex, KConstInt, KConstString
from dsl.kconfig.core import KElement, KStringKey
from dsl.kconfig.var import KConst, KExpr, KExpr, KVar

class KOption[ConstT:KConst](NodeBlock[KElement,TextNode],GenericArgsMixin):
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
        self._const_type:KConst=self.get_arg(0)

        if name is None:
            begin = TextNode(f"{keyword}")
        else:
            begin = TextNode(f"{keyword} {name}")

        super().__init__(begin)

        if prompt is None:
            self.append(TextNode(self._const_type.typename()))
        else:
            self.append(KStringKey(self._const_type.typename(), prompt))

        self._default_list=WordAlignedStack[TextNode]()
        self._dependency_list=WordAlignedStack[TextNode]()
        self._select_list=WordAlignedStack[TextNode]()

        self.append(self._default_list)
        self.append(self._dependency_list)
        self.append(self._select_list)

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

        if when is None or KConst.isTrue(when):
            self._default_list.append(TextNode(f"default {value}"))
        else:
            self._default_list.append(TextNode(f"default {value} if {when}"))
        return self

    def add_depends(self, *conds: KExpr) -> "KOption[ConstT]":
        for cond in conds:
            if not KConst.isTrue(cond):
                self._dependency_list.append(TextNode(f"depends on {cond}"))
        return self
    
    def add_selects(self, *vars: KExpr) -> "KOption[ConstT]":
        for var in vars:
            self._select_list.append(TextNode(f"select {var}"))
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
