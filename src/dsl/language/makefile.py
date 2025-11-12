#!/usr/bin/env python3
from __future__ import annotations

from typing import List, Optional, Union

from dsl.core import render


from dsl.core.var import VarExpr, VarName  # type: ignore
from dsl.variable.makefile import  MVar,MExpr2  # type: ignore

Element = render.Node


# ===== Comments and banners =====

class Comment(render.Text):
    def __init__(self, text: str):
        super().__init__(f"# {text}" if text else "#")


class Banner(render.Node):
    def __init__(self, title: str, width: int = 60, char: str = "#"):
        self._title = title.strip()
        self._char = char[0] if char else "#"
        self._width = max(width, len(self._title) + 4)

    @property
    def lines(self) -> List[str]:
        bar = self._char * self._width
        if not self._title:
            return [bar]
        mid = f"{self._char} {self._title} {self._char}"
        if len(mid) < self._width:
            mid += " " * (self._width - len(mid))
        return [bar, mid, bar]


class BlankLine(render.BlankLine):
    pass


# ===== Assignments (LHS is a var) =====

class Assignment(render.Text):
    """
    VAR op VALUE

    Operators:
      =    recursive
      :=   simple
      ?=   set if not set
      +=   append
    """
    def __init__(self, var:MVar, value: Union[MVar,str], op: str = "="):
        op = op.strip()
        if op not in ("=", ":=", "?=", "+="):
            raise ValueError(f"Invalid assignment operator: {op}")
        super().__init__(f"{var} {op} {value}")


class Set(Assignment):
    def __init__(self, var:MVar, value: Union[MVar,str]):
        super().__init__(var, value, "=")


class SetImmediate(Assignment):
    def __init__(self, var:MVar, value: Union[MVar,str]):
        super().__init__(var, value, ":=")


class SetDefault(Assignment):
    def __init__(self, var:MVar, value: Union[MVar,str]):
        super().__init__(var, value, "?=")


class Append(Assignment):
    def __init__(self, var:MVar, value: Union[MVar,str]):
        super().__init__(var, value, "+=")


# ===== Conditionals =====

class _BaseIf(render.Block):
    """
    Block with else-if chaining and else body.

    begin:  "if ..." | "ifdef ..." | "ifndef ..." | "ifeq (...)" | "ifneq (...)"
    end:    "endif"

    Else-if rendering rule:
      for cond in _conditions:
          cond_lines = cond.lines
          if len(cond_lines) >= 2:
              emit "else " + cond_lines[0]
              emit cond_lines[1:-1]   # skip inner "endif"
    """
    def __init__(
        self,
        header: str,
        *,
        margin: Optional[render.Node] = None,
        inner: bool = True,
        outer: bool = False,
    ):
        header = header.strip()
        if not header:
            raise ValueError("Empty conditional header")

        super().__init__(
            begin=render.Text(header),
            end=render.Text("endif"),
            margin=margin,
            inner=inner,
            outer=outer,
        )

        self._conditions: render.Stack["_BaseIf"] = render.Stack(
            margin=margin, inner=inner, outer=outer
        )
        self._otherwise: render.Stack[Element] = render.Stack(
            margin=margin, inner=inner, outer=outer
        )

    @property
    def conditions(self) -> render.Stack["_BaseIf"]:
        return self._conditions

    @property
    def otherwise(self) -> render.Stack[Element]:
        return self._otherwise

    @property
    def lines(self) -> List[str]:
        out: List[str] = super().lines
        if not out:
            return out

        endif_line = out.pop()

        for cond in self._conditions:
            cond_lines = cond.lines
            if len(cond_lines) >= 2:
                out.append("else " + cond_lines[0])
                out.extend(cond_lines[1:-1])

        else_lines = self._otherwise.lines
        if else_lines:
            out.append("else")
            out.extend(render.Node.indent(1, else_lines))

        out.append(endif_line)
        return out


class If(_BaseIf):
    def __init__(self, condition: Union[str, MExpr2], **kw):
        super().__init__(f"if {str(condition).strip()}", **kw)


class IfDef(_BaseIf):
    def __init__(self, var: MVar, **kw):
        super().__init__(f"ifdef {var}", **kw)


class IfNDef(_BaseIf):
    def __init__(self, var: MVar, **kw):
        super().__init__(f"ifndef {var}", **kw)


class IfEq(_BaseIf):
    def __init__(self, a: Union[str, MExpr2], b: Union[str, MExpr2], **kw):
        super().__init__(f"ifeq ({a},{b})", **kw)


class IfNEq(_BaseIf):
    def __init__(self, a: Union[str, MExpr2], b: Union[str, MExpr2], **kw):
        super().__init__(f"ifneq ({a},{b})", **kw)


# ===== define / endef =====

class Define(render.Block):
    def __init__(self, name: str, *body: Element):
        name = name.strip()
        if not name:
            raise ValueError("Macro name cannot be empty")

        begin = render.Text(f"define {name}")
        end = render.Text("endef")

        super().__init__(
            begin=begin,
            end=end,
            margin=None,
            inner=False,
            outer=False,
        )
        self.extend(body)
