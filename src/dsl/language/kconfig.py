#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union

from dsl.core import dsl
VarName=str


Element = dsl.Node


class StringKey(dsl.Text):
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

class TypedOption(dsl.Block, ABC):
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
        name: VarName,
        type_keyword: str,
        prompt: Optional[str] = None,
        menuconfig: bool = False,
    ):
        keyword = "menuconfig" if menuconfig else "config"

        # First line, not indented.
        begin = dsl.Text(f"{keyword} {name}")

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
            self.append(dsl.Text(type_keyword))
        else:
            # bool "Prompt", string "Prompt", etc.
            self.append(StringKey(type_keyword, prompt))

    @abstractmethod
    def _format_default_value(self, default: Union[str, int, bool]) -> str:
        """
        Subclasses implement formatting for non-VarName values.
        """

    def format_default(
        self,
        default: Union[str, int, bool, VarName],
    ) -> str:
        """
        Shared handling:
          - VarName is always treated as a symbol reference (no quotes).
          - Other types are delegated to _format_default_value.
        """
        if isinstance(default, VarName):
            return str(default)
        return self._format_default_value(default)

    def add_default(
        self,
        value: Union[str, int, bool, VarName],
        when: Optional[VarName] = None,
    ) -> "TypedOption":
        v = self.format_default(value)
        if when is None:
            self.append(dsl.Text(f"default {v}"))
        else:
            self.append(dsl.Text(f"default {v} if {when}"))
        return self

    def add_depends(self, *conds: VarName) -> "TypedOption":
        for cond in conds:
            self.append(dsl.Text(f"depends on {cond}"))
        return self


class Bool(TypedOption):
    def __init__(
        self,
        name: VarName,
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
        name: VarName,
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
        name: VarName,
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
        name: VarName,
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

    def __init__(self, name: VarName, prompt: str):
        super().__init__(name, prompt, menuconfig=True)


# ===== Block constructs: if / menu =====

class BlockElement(dsl.Block):
    """
    Helper for simple:

      statement
          <children...>
      end<keyword>
    """

    def __init__(self, statement: str, *children: Element):
        if statement:
            keyword = statement.split()[0].lower()
            begin = dsl.Text(statement)
            end = dsl.Text(f"end{keyword}")
        else:
            begin = None
            end = None

        super().__init__(
            begin=begin,
            end=end,
            margin=dsl.VSpace(1),
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

    def __init__(self, condition: VarName, *blocks: Element):
        super().__init__(f"if {condition}", *blocks)


class Menu(BlockElement):
    """
    menu "Title"
        ...
    endmenu
    """

    def __init__(self, title: str, *blocks: Element):
        statement = f'menu "{StringKey.escape(title)}"'
        super().__init__(statement, *blocks)


# ===== Choice: special header block =====

class Choice(dsl.Block):
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
        header = dsl.Block(
            begin=dsl.Text("choice"),
            end=None,
            margin=None,
            inner=False,
            outer=False,
        )
        header.append(StringKey("prompt", prompt))
        header.append(dsl.Text(type_keyword))

        # Main Choice block:
        # begin = header (already rendered as choice + its properties)
        # children = actual alternatives
        # end = endchoice
        super().__init__(
            begin=header,
            end=dsl.Text("endchoice"),
            margin=None,
            inner=False,
            outer=False,
        )
        self.extend(choices)


# ===== Simple one-line elements =====

class Source(StringKey):
    def __init__(self, path: str):
        super().__init__("source", path)


class Comment(StringKey):
    def __init__(self, comment: str):
        super().__init__("comment", comment)
