# ===== Typed options: config / menuconfig =====

from typing import Generic, Optional, TypeVar, Union
from dsl.kconfig.const import KConstBool, KConstHex, KConstInt, KConstString
from dsl.kconfig.lang import KConfig, KElement, KStringKey
from dsl.kconfig.var import KConst, KExpr, KVar
from dsl.lang import NULL, Block, Node, NullNode, Text
from dsl.typing_utils import resolve_generic_type_arg


ConstT = TypeVar("ConstT", bound=KConst)


class KOption(Block[KElement,Text,NullNode], Generic[ConstT]):
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
        self._const_type: type[KConst] = resolve_generic_type_arg(self,index=0,expected=KConst)

        if name is None:
            begin = Text(f"{keyword}")
        else:
            begin = Text(f"{keyword} {name}")

        super().__init__(begin, NULL)

        if prompt is None:
            self.append(Text(self._const_type.typename()))
        else:
            self.append(KStringKey(self._const_type.typename(), prompt))

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
            self.append(Text(f"default {value}"))
        else:
            self.append(Text(f"default {value} if {when}"))
        return self

    def add_depends(self, *conds: KExpr) -> "KOption[ConstT]":
        for cond in conds:
            if not KConst.isTrue(cond):
                self.append(Text(f"depends on {cond}"))
        return self
    
    def add_selects(self, *vars: KVar) -> "KOption[ConstT]":
        for var in vars:
            self.append(Text(f"select {var}"))
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
