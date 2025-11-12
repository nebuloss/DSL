#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union

from dsl.core import render
from dsl.variable import kconfig


Element = render.Node


class StringKey(render.Text):
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
        super().__init__(f'{keyword} "{self.escape(value)}"')


# ===== Typed options: config / menuconfig =====

from typing import Optional, Union

class TypedOption(render.Block, ABC):
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
        name: kconfig.KVar,
        type_keyword: str,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        keyword = "menuconfig" if menuconfig else "config"
        begin = render.Text(f"{keyword} {name}")
        super().__init__(begin=begin, end=None, margin=None, inner=False, outer=False)

        if prompt is None:
            self.append(render.Text(type_keyword))
        else:
            self.append(StringKey(type_keyword, prompt))

    def add_default(
        self,
        value: kconfig.KExpr,
        when: Optional[kconfig.KVar] = None,
    ) -> "TypedOption":

        if when is None:
            self.append(render.Text(f"default {value}"))
        else:
            self.append(render.Text(f"default {value} if {when}"))
        return self

    def add_depends(self, *conds: kconfig.KVar) -> "TypedOption":
        for cond in conds:
            self.append(render.Text(f"depends on {cond}"))
        return self

class Bool(TypedOption):
    def __init__(
        self,
        name: kconfig.KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "bool", prompt, menuconfig=menuconfig)

    def add_default(
        self,
        value: kconfig.KExpr,
        when: Optional[kconfig.KVar] = None,
    ) -> "Bool":
        if isinstance(value, kconfig.KConst) and value.val_type != "bool":
            raise TypeError("Bool default must be a KConst of type 'bool'")
        return super().add_default(value, when)
    
class String(TypedOption):
    def __init__(
        self,
        name: kconfig.KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "string", prompt, menuconfig=menuconfig)

    def add_default(
        self,
        value: Union[kconfig.KConst, kconfig.KVar],
        when: Optional[kconfig.KVar] = None,
    ) -> "String":
        if isinstance(value, kconfig.KConst) and value.val_type != "string":
            raise TypeError("String default must be a KConst of type 'string'")
        return super().add_default(value, when)
    
class Int(TypedOption):
    def __init__(
        self,
        name: kconfig.KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "int", prompt, menuconfig=menuconfig)

    def add_default(
        self,
        value: Union[kconfig.KConst, kconfig.KVar],
        when: Optional[kconfig.KVar] = None,
    ) -> "Int":
        if isinstance(value, kconfig.KConst) and value.val_type != "int":
            raise TypeError("Int default must be a KConst of type 'int'")
        return super().add_default(value, when)

class Hex(TypedOption):
    def __init__(
        self,
        name: kconfig.KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "hex", prompt, menuconfig=menuconfig)

    def add_default(
        self,
        value: Union[kconfig.KConst, kconfig.KVar],
        when: Optional[kconfig.KVar] = None,
    ) -> "Hex":
        if isinstance(value, kconfig.KConst) and value.val_type != "hex":
            raise TypeError("Hex default must be a KConst of type 'hex'")
        return super().add_default(value, when)


class Menuconfig(Bool):
    """
    Convenience wrapper:

      menuconfig NAME
          bool "Prompt"
          ...
    """

    def __init__(self, name: kconfig.KVar, prompt: str):
        super().__init__(name, prompt, menuconfig=True)


# ===== Block constructs: if / menu =====

class BlockElement(render.Block):
    """
    Helper for simple:

      statement
          <children...>
      end<keyword>
    """

    def __init__(self, begin: render.Node, *children: Element):
        if begin is None:
            raise ValueError("Expecting begin statement")

        words = str(begin).split()
        if not words:
            raise ValueError("Empty begin is not allowed")

        keyword = words[0].lower()
        end = render.Text(f"end{keyword}")

        super().__init__(
            begin=begin,
            end=end,
            margin=render.BlankLine(1),
            inner=True,
            outer=True,
        )
        self.extend(children)


class If(BlockElement):
    """
    if CONDITION
        ...
    endif
    """

    def __init__(self, condition: kconfig.KVar, *blocks: Element):
        super().__init__(render.Text(f"if {condition}"), *blocks)


class Menu(BlockElement):
    """
    menu "Title"
        ...
    endmenu
    """

    def __init__(self, title: str, *blocks: Element):
        super().__init__(StringKey("menu", title), *blocks)


# ===== Choice: special header block =====

class Choice(BlockElement):
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
        *choices: Element,
        type_keyword: str = "bool",
    ):
        # Header:
        #   choice
        #       prompt "..."
        #       <type_keyword>
        header = (
            render.Block(
                begin=render.Text("choice"),
                end=None,
                margin=None,
                inner=False,
                outer=False,
            )
            .append(StringKey("prompt", prompt))
            .append(render.Text(type_keyword))
        )

        # Main Choice block:
        # begin = header (choice + its properties)
        # children = actual alternatives
        # end = endchoice
        super().__init__(begin=header, *choices)


# ===== Simple one-line elements =====

class Source(StringKey):
    def __init__(self, path: str):
        super().__init__("source", path)


class Comment(StringKey):
    def __init__(self, comment: str):
        super().__init__("comment", comment)
