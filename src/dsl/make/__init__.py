# dsl/makefile/__init__.py

from __future__ import annotations

from dataclasses import dataclass

from .var import (
    MExpr,
    MNull,
    MConst,
    MVar,
    MArg,
    MAdd,
    MAnd,      # imported but not exposed
    MOr,       # imported but not exposed
    MFunc,
    MIf as MIfFunc,   # $(if ...) function
    MEval,
    MShell,
    MCall,
    MForeach,
    MNot,      # imported but not exposed
)

from .lang import (
    MElement,
    Makefile,
    MAppend,
    MAssignment,
    MAssignments,
    MCommand,
    MComment,
    MSet,
    MSetImmediate,
    MSetDefault,
    MRule,
    MPhony,
    MInclude,
    MShellCommand,
    MDefine,
    MIf as MKwIf,     # "if ... endif" block
    MIfDef,
    MIfNDef,
    MIfEq,
    MIfNEq,
    MExprLine,
)

# ---------------------------------------------------------------------
# Core expression aliases
# ---------------------------------------------------------------------

MExpr = MExpr
MConst = MConst
Var = MVar
Arg = MArg
Add = MAdd
Func = MFunc
MNull = MNull

# lowercase convenience aliases for classes
expr = MExpr
const = MConst
var = MVar

# Convenience constants
true = MConst.true()
false = MConst.false()
null = MNull()


def all(*vars: Var) -> MExpr:
    """
    Logical AND over a sequence of Var.
    all(a, b, c) becomes a & b & c, starting from true.
    """
    result: MExpr = true
    for v in vars:
        result &= v
    return result


def any(*vars: Var) -> MExpr:
    """
    Logical OR over a sequence of Var.
    any(a, b, c) becomes a | b | c, starting from false.
    """
    result: MExpr = false
    for v in vars:
        result |= v
    return result


def arg(n: int) -> Arg:
    """
    Convenience helper for automatic argument vars: $(1), $(2), ...

    Example:
        m.func.call(m.var("my_macro"), m.arg(1))
    """
    return Arg(n)


def expr(e: MExpr) -> MExprLine:
    """
    Wrap an expression as a top level Makefile element.

    Equivalent to constructing MExprLine(e) directly.
    """
    return MExprLine(e)


# ---------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class FuncNS:
    """
    Namespace for Make functions.

    Usage:
        func.test(cond, then, else_)
        func.eval(expr)
        func.shell(expr)
        func.call(macro, arg1, arg2)
        func.foreach(var, list_expr, body)
    """

    test: type[MIfFunc] = MIfFunc
    eval: type[MEval] = MEval
    shell: type[MShell] = MShell
    call: type[MCall] = MCall
    foreach: type[MForeach] = MForeach


@dataclass(frozen=True)
class KeywordNS:
    """
    Namespace for Make keywords / conditionals / directives.

    Usage:
        keyword.test(expr, body...)
        keyword.ifeq(a, b, body...)
        keyword.ifneq(a, b, body...)
        keyword.ifdef(var, body...)
        keyword.ifndef(var, body...)
        keyword.define(var, body...)
        keyword.include("path.mk")
    """

    test: type[MKwIf] = MKwIf      # if ... endif
    ifdef: type[MIfDef] = MIfDef
    ifndef: type[MIfNDef] = MIfNDef
    ifeq: type[MIfEq] = MIfEq
    ifneq: type[MIfNEq] = MIfNEq
    define: type[MDefine] = MDefine
    include: type[MInclude] = MInclude


@dataclass(frozen=True)
class AssignmentNS:
    """
    Namespace for Make variable assignments.

    Usage:
        assignment.set(VAR, EXPR)
        assignment.immediate(VAR, EXPR)
        assignment.default(VAR, EXPR)
        assignment.append(VAR, EXPR)
        assignment.list(assignment.set(...), assignment.append(...))
    """

    set: type[MSet] = MSet
    immediate: type[MSetImmediate] = MSetImmediate
    default: type[MSetDefault] = MSetDefault
    append: type[MAppend] = MAppend
    list: type[MAssignments] = MAssignments


func = FuncNS()
keyword = KeywordNS()
assignment = AssignmentNS()


# ---------------------------------------------------------------------
# Structural / file level API
# ---------------------------------------------------------------------

Element = MElement
File = Makefile
rule = MRule
phony = MPhony
shell = MShellCommand
command = MCommand
comment = MComment

__all__ = [
    # expression core
    "MExpr",
    "MConst",
    "Var",
    "Arg",
    "Func",

    # lowercase / helpers
    "const",
    "var",
    "arg",

    # expression helpers
    "true",
    "false",
    "null",
    "all",
    "any",
    "expr",

    # namespaces
    "func",
    "keyword",
    "assignment",

    # file / structure API
    "Element",
    "File",
    "command",
    "comment",
    "rule",
    "phony",
    "shell",
]
