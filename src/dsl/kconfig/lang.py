#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC
from typing import Generic, Optional, Self, TypeVar, Union, get_args

from dsl import Node,Text,Stack,BlankLine,SimpleStack,Block
from .var import KConstBool, KConstHex, KConstInt, KConstString, KExpr,KVar,KConst


KElement = Node

class KConfig(Stack[KElement]):
    MARGIN:Optional[Node]=BlankLine()

    def __init__(self,*elements:KElement):
        super().__init__(*elements,inner=self.MARGIN, outer=None)

class KList(SimpleStack[KElement]):
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


# ===== Typed options: config / menuconfig =====

ConstT = TypeVar("ConstT", bound=KConst)


class KTypedOption(Block[KElement], Generic[ConstT]):
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
        name: KVar,
        type_keyword: str,
        *,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        self._name = name
        # Resolve ConstT from generics (like VarExpr does for OpsT)
        self._const_type: type[KConst] = self._resolve_type_arg(
            index=0,
            expected=KConst,
        )

        keyword = "menuconfig" if menuconfig else "config"
        begin = Text(f"{keyword} {name}")

        super().__init__(begin=begin, end=None, inner=None, outer=None)

        if prompt is None:
            self.append(Text(type_keyword))
        else:
            self.append(KStringKey(type_keyword, prompt))

    @property
    def name(self) -> KVar:
        return self._name

    # ---------- generic parameter resolution (VarExpr-style) ----------

    def _resolve_type_arg(self, *, index: int, expected: type) -> type:
        """
        Resolve generic type argument at position `index` that is a
        subclass of `expected`. Looks at instance __orig_class__ and
        then walks the MRO to inspect each base's __orig_bases__.

        This lets it work even for second-level subclasses like
        KMenuconfig(KBool), where the generic lives on KBool.
        """

        # Instance-level generic, e.g. opt: KBool = KBool(...)
        orig = getattr(self, "__orig_class__", None)
        if orig is not None:
            args = get_args(orig)
            if len(args) > index:
                cand = args[index]
                if isinstance(cand, type) and issubclass(cand, expected):
                    return cand

        # Walk MRO and check each base's __orig_bases__
        for base in type(self).mro():
            for gb in getattr(base, "__orig_bases__", ()):
                args = get_args(gb)
                if len(args) > index:
                    cand = args[index]
                    if isinstance(cand, type) and issubclass(cand, expected):
                        return cand

        raise TypeError(
            f"Could not resolve generic parameter {index} as subclass of "
            f"{expected.__name__} for {type(self).__name__}. "
            "Declare your node as KTypedOption[YourConstType]."
        )

    # ---------- DSL helpers ----------

    def add_default(
        self,
        value: Union[KVar, ConstT],
        when: Optional[KExpr] = None,
    ) -> KTypedOption[ConstT]:
        """
        Add a 'default' line.

        value:
          - KVar   -> used directly as symbol name
          - ConstT -> must match this option's constant type
        """
        if isinstance(value, KVar):
            v_str = str(value)
        else:
            # runtime check that matches the generic ConstT
            if not isinstance(value, self._const_type):
                raise TypeError(
                    f"Default constant for {type(self).__name__} "
                    f"must be {self._const_type.__name__}, "
                    f"got {type(value).__name__}"
                )
            v_str = str(value)

        if when is None or KConst.isTrue(when):
            self.append(Text(f"default {v_str}"))
        else:
            self.append(Text(f"default {v_str} if {when}"))
        return self

    def add_depends(self, *conds: KExpr) -> KTypedOption[ConstT]:
        for cond in conds:
            if not KConst.isTrue(cond):
                self.append(Text(f"depends on {cond}"))
        return self


# ---------- concrete typed options ----------

class KBool(KTypedOption[KConstBool]):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "bool", prompt=prompt, menuconfig=menuconfig)


class KString(KTypedOption[KConstString]):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "string", prompt=prompt, menuconfig=menuconfig)


class KInt(KTypedOption[KConstInt]):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "int", prompt=prompt, menuconfig=menuconfig)


class KHex(KTypedOption[KConstHex]):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "hex", prompt=prompt, menuconfig=menuconfig)


class KMenuconfig(KBool):
    """
    Convenience wrapper:

      menuconfig NAME
          bool "Prompt"
          ...
    """

    def __init__(self, name: KVar, prompt: str):
        super().__init__(name, prompt=prompt, menuconfig=True)




# ===== Block constructs: if / menu =====

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
        type_keyword: str = "bool",
    ):
        # Header:
        #   choice
        #       prompt "..."
        #       <type_keyword>
        header = Block(
                begin=Text("choice"),
                end=None,
                inner=None,
                outer=None
            ).extend((
                KStringKey("prompt", prompt),
                Text(type_keyword)
            ))

        # Main Choice block:
        # begin = header (choice + its properties)
        # children = actual alternatives
        # end = endchoice
        super().__init__(header, *choices)


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
