#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC
import re
from typing import Optional, Union

from dsl.core import language
from dsl.variable import kconfig


KElement = language.Node

class KConfig(language.Stack[KElement]):
    def __init__(self):
        super().__init__(language.BlankLine(), True, False)

class KStringKey(language.Text):
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

class KTypedConfig(language.Block[KElement], ABC):
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
        begin = language.Text(f"{keyword} {name}")
        super().__init__(begin=begin, end=None, margin=None, inner=False, outer=False)

        if prompt is None:
            self.append(language.Text(type_keyword))
        else:
            self.append(KStringKey(type_keyword, prompt))

    def add_default(
        self,
        value: kconfig.KExpr,
        when: Optional[kconfig.KVar] = None,
    ) -> "KTypedConfig":

        if when is None or kconfig.KConst.isTrue(when):
            self.append(language.Text(f"default {value}"))
        else:
            self.append(language.Text(f"default {value} if {when}"))
        return self

    def add_depends(self, *conds: kconfig.KVar) -> "KTypedConfig":
        for cond in conds:
            if not kconfig.KConst.isTrue(cond):
                self.append(language.Text(f"depends on {cond}"))
        return self

class KBool(KTypedConfig):
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
    ) -> "KBool":
        if isinstance(value, kconfig.KConst) and value.val_type != "bool":
            raise TypeError("Bool default must be a KConst of type 'bool'")
        return super().add_default(value, when)
    
class KString(KTypedConfig):
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
    ) -> "KString":
        if isinstance(value, kconfig.KConst) and value.val_type != "string":
            raise TypeError("String default must be a KConst of type 'string'")
        return super().add_default(value, when)
    
class KInt(KTypedConfig):
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
    ) -> "KInt":
        if isinstance(value, kconfig.KConst) and value.val_type != "int":
            raise TypeError("Int default must be a KConst of type 'int'")
        return super().add_default(value, when)

class KHex(KTypedConfig):
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
    ) -> "KHex":
        if isinstance(value, kconfig.KConst) and value.val_type != "hex":
            raise TypeError("Hex default must be a KConst of type 'hex'")
        return super().add_default(value, when)


class KMenuconfig(KBool):
    """
    Convenience wrapper:

      menuconfig NAME
          bool "Prompt"
          ...
    """

    def __init__(self, name: kconfig.KVar, prompt: str):
        super().__init__(name, prompt, menuconfig=True)


# ===== Block constructs: if / menu =====

class KBlock(language.Block[KElement]):
    """
    Helper for simple:

      statement
          <children...>
      end<keyword>
    """

    def __init__(self, begin: language.Node, *children: KElement):
        if begin is None:
            raise ValueError("Expecting begin statement")

        words = str(begin).split()
        if not words:
            raise ValueError("Empty begin is not allowed")

        keyword = words[0].lower()
        end = language.Text(f"end{keyword}")

        super().__init__(
            begin=begin,
            end=end,
            margin=language.BlankLine(),
            inner=True,
            outer=True,
        )
        self.extend(children)


class KIf(KBlock):
    """
    if CONDITION
        ...
    endif
    """

    def __init__(self, condition: kconfig.KVar, *blocks: KElement):
        super().__init__(language.Text(f"if {condition}"), *blocks)


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
        header = language.Block(
                begin=language.Text("choice"),
                end=None,
                margin=None,
                inner=False,
                outer=False,
            ).extend((
                KStringKey("prompt", prompt),
                language.Text(type_keyword)
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
      KSource("boards/$(BOARD)/Kconfig", normalize_vars=True)
        -> source "boards/$BOARD/Kconfig"
    """

    _VAR_RE = re.compile(r"\$\((\w+)\)")

    @classmethod
    def _normalize_vars(cls, s: str) -> str:
        """Convert Make-style $(FOO) into Kconfig-style $FOO."""
        return cls._VAR_RE.sub(r"$\1", s)

    def __init__(self, path: str, normalize_vars: bool = False):
        if not isinstance(path, str):
            raise TypeError("source path must be a string")

        if normalize_vars:
            path = self._normalize_vars(path)

        super().__init__("source", path)


class KComment(KStringKey):
    def __init__(self, comment: str):
        super().__init__("comment", comment)
