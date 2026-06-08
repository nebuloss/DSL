"""
Kconfig option nodes: config, menuconfig, choice header.

KOption is a NodeBlock whose children are built up via a fluent builder API
(add_default, add_depends, add_selects, add_range, add_help).  The mutable
lists (_range_list, _default_list, …) are passed to NodeBlock at construction
time, so appending to them after the fact is reflected in the rendered output
— ListNode stores references, not copies.

add_help() is the exception: it appends a fresh NodeBlock directly to self
(the option's own _items) rather than to a pre-allocated sub-list.  This
keeps help always last and avoids reserving an empty slot when no help is
needed.

The concrete type (bool/string/int/hex) is encoded as a generic argument:
  KOption[KBool]   →  const_type.TYPE == "bool"
  KOptionBool      — shorthand subclass
"""
# ===== Typed options: config / menuconfig =====

from typing import Optional, Union
from dsl.container import NodeBlock
from dsl.content import TextNode, WordAlignedStack, WordlistNode
from dsl.generic_args import GenericArgsMixin
from dsl.kconfig.core import KConst, KElement
from dsl.kconfig.var import KBool, KExpr, KHex, KInt, KString, KVar

class KOption[ConstT:KConst](GenericArgsMixin,NodeBlock[KElement,TextNode]):
    """
    Generic typed symbol:

      config NAME
          <type_keyword> ["Prompt"]
          [range MIN MAX [if COND]]
          [default ...]
          [depends on ...]
          [select ...]
          [help
            ...]
    or:
      menuconfig NAME
          ...
    """

    def __init__(
        self,
        name: Optional[KVar | str],
        prompt: Optional[str] = None,
        keyword:str="config",
    ):
        self._name = KVar.coerce(name) if name is not None else None
        # Resolve ConstT from generics (like VarExpr does for OpsT)
        const_type:KConst=self.get_arg(0)
        self._const_type = const_type

        begin_node = WordlistNode(keyword)
        prompt_node=WordlistNode(const_type.TYPE)

        if self._name:
            begin_node.append(self._name)

        if prompt:
            prompt_node.append(KString(prompt))

        self._range_list=WordAlignedStack[WordlistNode]()
        self._default_list=WordAlignedStack[WordlistNode]()
        self._dependency_list=WordAlignedStack[WordlistNode]()
        self._select_list=WordAlignedStack[WordlistNode]()

        super().__init__(
            begin_node,
            prompt_node,
            self._range_list,
            self._default_list,
            self._dependency_list,
            self._select_list
        )

    @property
    def name(self) -> KVar:
        return self._name

    # ---------- DSL helpers ----------

    def add_range(
        self,
        min_val: Union[KVar, KInt, KHex, int, str],
        max_val: Union[KVar, KInt, KHex, int, str],
        when: Optional[KExpr | str] = None,
    ) -> "KOption[ConstT]":
        """Add a 'range MIN MAX [if COND]' line (for int/hex options)."""
        wl = WordlistNode("range", self._const_type.coerce(min_val), self._const_type.coerce(max_val))
        when = self._coerce_cond(when)
        if when is not None and not KBool.isTrue(when):
            wl.append("if")
            wl.append(when)
        self._range_list.append(wl)
        return self

    @staticmethod
    def _coerce_cond(when: Optional[KExpr | str]) -> Optional[KExpr]:
        """A bare str condition is a symbol reference -> KVar (normalised)."""
        return KVar.coerce(when) if isinstance(when, str) else when

    def add_default(
        self,
        value: Union[KVar, ConstT, str, int, bool],
        when: Optional[KExpr | str] = None,
    ) -> "KOption[ConstT]":
        """
        Add a 'default' line.

        value:
          - KVar    -> used directly as symbol name
          - ConstT  -> must match this option's constant type
          - raw str/int/bool -> wrapped as this option's constant type
        """
        wl=WordlistNode("default", self._const_type.coerce(value))
        self._default_list.append(wl)

        when = self._coerce_cond(when)
        if when is not None and not KBool.isTrue(when):
            wl.append("if")
            wl.append(when)

        return self

    def add_depends(self, *conds: KExpr | str) -> "KOption[ConstT]":
        for cond in conds:
            cond = KVar.coerce(cond) if isinstance(cond, str) else cond
            if not KBool.isTrue(cond):
                self._dependency_list.append(WordlistNode("depends on",cond))
        return self

    def add_selects(self, *vars: KVar | str) -> "KOption[ConstT]":
        for var in vars:
            self._select_list.append(WordlistNode("select", KVar.coerce(var)))
        return self

    def add_help(self, *lines: str) -> "KOption[ConstT]":
        """Add a help block. Each string is one line of help text."""
        if lines:
            help_block = NodeBlock(TextNode("help"), *[TextNode(line) for line in lines], level=1)
            self.append(help_block)
        return self


# ---------- concrete typed options ----------

class KOptionBool(KOption[KBool]):
    def __init__(
        self,
        name: KVar | str,
        prompt: Optional[str] = None,
    ):
        super().__init__(name, prompt)


class KOptionString(KOption[KString]):
    def __init__(self, name: KVar | str, prompt: Optional[str] = None):
        super().__init__(name, prompt)


class KOptionInt(KOption[KInt]):
    def __init__(self, name: KVar | str, prompt: Optional[str] = None):
        super().__init__(name,prompt)


class KOptionHex(KOption[KHex]):
    def __init__(self, name: KVar | str, prompt: Optional[str] = None):
        super().__init__(name, prompt)


class KMenuConfig(KOption[KBool]):
    def __init__(self, name: KVar | str, prompt: str):
        super().__init__(name,prompt, keyword="menuconfig")

class KChoiceHeader(KOption[KBool]):
    def __init__(self, prompt: str):
        super().__init__(None, prompt, keyword="choice")
