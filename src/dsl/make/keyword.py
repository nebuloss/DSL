from typing import List, Tuple
from dsl.lang import Block, Node, SimpleStack, Stack, Text
from dsl.make.lang import MElement, Makefile
from dsl.make.var import MExpr, MVar

class MDefine(Block[MElement]):
    """
    Multi-line define / endef macro:

        define FOO
            ...
        endef

    `name` must be an MVar (only `name.name` is used, not $(NAME)).
    """

    def __init__(self, name: MVar, *body: MElement):
        if not isinstance(name, MVar):
            raise TypeError(f"Macro name must be MVar, got {type(name).__name__}")
        macro = name.name.strip()
        if not macro:
            raise ValueError("Macro name cannot be empty")

        begin = Text(f"define {macro}")
        end = Text("endef")

        super().__init__(
            *body,
            begin=begin,
            end=end,
            inner=Makefile.MARGIN,
            outer=None
        )

class MIfExpr(Block[MElement]):
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

    def __init__(
        self,
        header: str,
        *body: MElement,
    ):
        super().__init__(
            *body,
            begin=Text(header.strip()),
            end=Text("endif"),
            inner=Makefile.MARGIN,
            outer=None
        )

    def split_parts(self) -> Tuple[str, List[str], str]:
        lines = self.lines
        if len(lines) < 2:
            raise ValueError("IfExpr must have at least a header and 'endif'")
        return lines[0], lines[1:-1], lines[-1]


class MIf(MIfExpr):
    def __init__(self, var: MVar, *body: MElement, **kw):
        super().__init__(f"if {var.name}", *body, **kw)


class MIfDef(MIfExpr):
    def __init__(self, var: MVar, *body: MElement, **kw):
        super().__init__(f"ifdef {var.name}", *body, **kw)


class MIfNDef(MIfExpr):
    def __init__(self, var: MVar, *body: MElement, **kw):
        super().__init__(f"ifndef {var.name}", *body, **kw)


class MIfEq(MIfExpr):
    def __init__(self, a: MExpr, b: MExpr, *body: MElement, **kw):
        super().__init__(f"ifeq ({a},{b})", *body, **kw)


class MIfNEq(MIfExpr):
    def __init__(self, a: MExpr, b: MExpr, *body: MElement, **kw):
        super().__init__(f"ifneq ({a},{b})", *body, **kw)


class MElse(MIfExpr):
    def __init__(self, *body):
        super().__init__("else", *body)


class MIfList(SimpleStack[MIfExpr]):
    @property
    def lines(self) -> List[str]:
        out: List[str] = []

        if not self.children:
            return out

        first_cond = self.children[0]
        if isinstance(first_cond, MElse):
            raise SyntaxError("Cannot have else statement at first position")

        # First branch: normal if / ifdef / ifndef / ifeq / ifneq
        first_header, first_body, shared_endif = first_cond.split_parts()
        out.append(first_header)
        out.extend(first_body)

        # Else-if branches and optional final else
        for cond in self.children[1:]:
            if isinstance(cond, MElse):
                # More permissive behavior: use the first Else and ignore anything after
                out.extend(cond.lines)
                return out

            header, body, _ = cond.split_parts()
            out.append(f"else {header}")
            out.extend(body)

        # No Else encountered: close with shared endif
        out.append(shared_endif)
        return out

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
