from abc import ABC, abstractmethod
from typing import Iterable, List, Tuple
from dsl.kconfig.var import KExpr
from dsl.lang import Block, IndentedNode, Node, SimpleStack, Stack, Text
from dsl.make.lang import MLine, MElement, Makefile
from dsl.make.var import MExpr, MVar

class MDefine(Block[MLine,Text,Text]):
    """
    Multi-line define / endef macro:

        define FOO
            ...
        endef

    `name` must be an MVar (only `name.name` is used, not $(NAME)).
    """

    def __init__(self, name: MVar, *body: MLine):
        if not isinstance(name, MVar):
            raise TypeError(f"Macro name must be MVar, got {type(name).__name__}")

        begin = Text(f"define {name}")
        end = Text("endef")

        super().__init__(
            *body,
            begin,
            end,
            inner=Makefile.MARGIN,
            outer=None
        )

class MCondition(Block[MElement,Text,Text],ABC):
    """
    Block with else-if chaining and else body.

    begin:  "if ..."   | "ifdef ..." | "ifndef ..." | "ifeq (...)" | "ifneq (...)"
    end:    "endif"

    Else-if rendering rule:
      for block in Elif:
          cond_lines = block.lines
          if len(cond_lines) >= 2:
              emit "else " + cond_lines[0]
              emit cond_lines[1:-1]   # skip inner "endif"
    """
    ENDIF=Text("endif")

    @classmethod
    @abstractmethod
    def keyword(cls)->str:
        raise NotImplemented

    def __init__(
        self,
        vars:Iterable[KExpr]=[],
        *body: MElement
    ):
        self._vars=vars

        super().__init__(
            self.generate_condition_statement(),
            self.ENDIF,
            *body,
            inner=Makefile.MARGIN,
        )

    def generate_condition_statement(self,else_keyword:bool=False)->Text:
        keyword=self.keyword()
        if else_keyword:
            keyword="else "+keyword
        elif not keyword:
            raise ValueError("empty condition statement not allowed")
        return Text(f"{keyword} ({",".join(var.name for var in self._vars)})")

class MIf(MCondition):
    @classmethod
    def keyword(cls):
        return "if"

    def __init__(self, var: MVar, *body: MElement):
        super().__init__([var], *body)


class MIfDef(MCondition):
    @classmethod
    def keyword(cls):
        return "ifdef"
    
    def __init__(self, var: MVar, *body: MElement):
        super().__init__([var], *body)


class MIfNDef(MCondition):
    @classmethod
    def keyword(cls):
        return "ifndef"
    
    def __init__(self, var: MVar, *body: MElement):
        super().__init__([var], *body)


class MIfEq(MCondition):
    @classmethod
    def keyword(cls):
        return "ifeq"
    
    def __init__(self, a: MExpr, b: MExpr, *body: MElement):
        super().__init__([a,b], *body)


class MIfNEq(MCondition):
    @classmethod
    def keyword(cls):
        return "ifneq"
    
    def __init__(self, a: MExpr, b: MExpr, *body: MElement):
        super().__init__([a,b], *body)


class MElse(MCondition):
    @classmethod
    def keyword(cls):
        return ""
    
    def __init__(self, *body):
        super().__init__("else", *body)


class MConditionList(Stack[MCondition]):
    def __iter__(self):
        nodes:List[Node]=[]
        for i,child in enumerate(self.children):
            nodes.append(child.generate_condition_statement(else_keyword=bool(i)))
            nodes.append(IndentedNode(child.toStack()))
        nodes.append(MCondition.ENDIF)
        yield from self.iter_with_margin(*nodes)

class MInclude(Text):
    """
    Makefile include line.

    - Escapes spaces in each path (foo bar -> foo\\ bar)
    - Supports multiple paths:
        MInclude("a.mk", "b mk") -> include a.mk b\\ mk
    """
    @staticmethod
    def _escape_spaces(path: str) -> str:
        """Escape spaces for use in a Makefile include."""
        # Make treats backslash-space as a single space character in the filename.
        return path.replace(" ", r"\ ")

    def __init__(self, *paths: str):
        if not paths:
            raise ValueError("MInclude requires at least one path")

        parts: list[str] = []

        for p in paths:
            if not isinstance(p, str):
                raise TypeError("include paths must be strings")
            
            p = self._escape_spaces(p)
            parts.append(p)

        line = "include " + " ".join(parts)
        super().__init__(line)
