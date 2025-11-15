#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC
from typing import Optional, Union

from dsl import Node,Text,Stack,BlankLine,SimpleStack,Block
from .var import KExpr,KVar,KConst


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

class KTypedConfig(Block[KElement], ABC):
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
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        keyword = "menuconfig" if menuconfig else "config"
        begin = Text(f"{keyword} {name}")
        super().__init__(begin=begin, end=None, inner=None, outer=None)

        if prompt is None:
            self.append(Text(type_keyword))
        else:
            self.append(KStringKey(type_keyword, prompt))

    def add_default(
        self,
        value: KExpr,
        when: Optional[KVar] = None,
    ) -> "KTypedConfig":

        if when is None or KConst.isTrue(when):
            self.append(Text(f"default {value}"))
        else:
            self.append(Text(f"default {value} if {when}"))
        return self

    def add_depends(self, *conds: KVar) -> "KTypedConfig":
        for cond in conds:
            if not KConst.isTrue(cond):
                self.append(Text(f"depends on {cond}"))
        return self

class KBool(KTypedConfig):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "bool", prompt, menuconfig=menuconfig)

    def add_default(
        self,
        value: KExpr,
        when: Optional[KVar] = None,
    ) -> "KBool":
        if isinstance(value, KConst) and value.val_type != "bool":
            raise TypeError("Bool default must be a KConst of type 'bool'")
        return super().add_default(value, when)
    
class KString(KTypedConfig):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "string", prompt, menuconfig=menuconfig)

    def add_default(
        self,
        value: Union[KConst, KVar],
        when: Optional[KVar] = None,
    ) -> "KString":
        if isinstance(value, KConst) and value.val_type != "string":
            raise TypeError("String default must be a KConst of type 'string'")
        return super().add_default(value, when)
    
class KInt(KTypedConfig):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "int", prompt, menuconfig=menuconfig)

    def add_default(
        self,
        value: Union[KConst, KVar],
        when: Optional[KVar] = None,
    ) -> "KInt":
        if isinstance(value, KConst) and value.val_type != "int":
            raise TypeError("Int default must be a KConst of type 'int'")
        return super().add_default(value, when)

class KHex(KTypedConfig):
    def __init__(
        self,
        name: KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "hex", prompt, menuconfig=menuconfig)

    def add_default(
        self,
        value: Union[KConst, KVar],
        when: Optional[KVar] = None,
    ) -> "KHex":
        if isinstance(value, KConst) and value.val_type != "hex":
            raise TypeError("Hex default must be a KConst of type 'hex'")
        return super().add_default(value, when)


class KMenuconfig(KBool):
    """
    Convenience wrapper:

      menuconfig NAME
          bool "Prompt"
          ...
    """

    def __init__(self, name: KVar, prompt: str):
        super().__init__(name, prompt, menuconfig=True)


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
