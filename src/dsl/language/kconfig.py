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

        # First line, not indented.
        begin = render.Text(f"{keyword} {name}")

        # Block indents all children by one level, no margins.
        super().__init__(
            begin=begin,
            end=None,
            margin=None,
            inner=False,
            outer=False,
        )

        # First child: type + optional prompt.
        if prompt is None:
            self.append(render.Text(type_keyword))
        else:
            # bool "Prompt", string "Prompt", etc.
            self.append(StringKey(type_keyword, prompt))

    @abstractmethod
    def _format_default_value(self, default: Union[str, int, bool]) -> str:
        """
        Subclasses implement formatting for non-kconfig.KVar values.
        """

    def format_default(
        self,
        default: Union[str, int, bool, kconfig.KVar],
    ) -> str:
        """
        Shared handling:
          - kconfig.KVar is always treated as a symbol reference (no quotes).
          - Other types are delegated to _format_default_value.
        """
        if isinstance(default, kconfig.KVar):
            return str(default)
        return self._format_default_value(default)

    def add_default(
        self,
        value: Union[str, int, bool, kconfig.KVar],
        when: Optional[kconfig.KVar] = None,
    ) -> "TypedOption":
        v = self.format_default(value)
        if when is None:
            self.append(render.Text(f"default {v}"))
        else:
            self.append(render.Text(f"default {v} if {when}"))
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

    def _format_default_value(self, default: Union[bool, str]) -> str:
        if isinstance(default, bool):
            return "y" if default else "n"
        if isinstance(default, str):
            v = default.strip().lower()
            if v in ("y", "n"):
                return v
        raise TypeError("Bool default must be bool or 'y'/'n'")


class String(TypedOption):
    def __init__(
        self,
        name: kconfig.KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "string", prompt, menuconfig=menuconfig)

    def _format_default_value(self, default: str) -> str:
        if isinstance(default, str):
            return f'"{StringKey.escape(default)}"'
        raise TypeError("String default must be str")


class Int(TypedOption):
    def __init__(
        self,
        name: kconfig.KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "int", prompt, menuconfig=menuconfig)

    def _format_default_value(self, default: Union[int, str]) -> str:
        if isinstance(default, int):
            return str(default)
        if isinstance(default, str) and default.strip().isdigit():
            return default.strip()
        raise TypeError("Int default must be int or decimal str")


class Hex(TypedOption):
    def __init__(
        self,
        name: kconfig.KVar,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        super().__init__(name, "hex", prompt, menuconfig=menuconfig)

    def _format_default_value(self, default: Union[int, str]) -> str:
        if isinstance(default, int):
            return f"0x{default:X}"
        if isinstance(default, str):
            s = default.strip()
            if s.lower().startswith("0x"):
                return s
            try:
                return f"0x{int(s, 16):X}"
            except ValueError:
                pass
        raise TypeError("Hex default must be int or hex str")


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
        if not begin:
            raise ValueError("Expecting begin statement")
        
        words=str(begin).split()
        if not words:
            raise ValueError("Empty begin is not allowed")
        
        keyword = words[0].lower()
        end = render.Text(f"end{keyword}")

        super().__init__(
            begin=begin,
            end=end,
            margin=render.VSpace(1),
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
        super().__init__(StringKey("menu",title), *blocks)


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
        # Header block:
        #   choice
        #       prompt "..."
        #       <type_keyword>
        header = render.Block(
                begin=render.Text("choice"),
                end=None,
                margin=None,
                inner=False,
                outer=False,
            ).append(StringKey("prompt", prompt)
            ).append(render.Text(type_keyword)
        )

        # Main Choice block:
        # begin = header (already rendered as choice + its properties)
        # children = actual alternatives
        # end = endchoice
        super().__init__(
            begin=header,
            *choices
        )


# ===== Simple one-line elements =====

class Source(StringKey):
    def __init__(self, path: str):
        super().__init__("source", path)


class Comment(StringKey):
    def __init__(self, comment: str):
        super().__init__("comment", comment)
