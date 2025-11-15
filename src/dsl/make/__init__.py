# dsl/makefile/__init__.py

from .var import (
    MExpr as Expr,
    MNull as Null,
    MConst as Const,
    MVar as Var,
    MArg as Arg,
    MAdd as Add,
    MAnd as And,
    MOr as Or,
    MFunc as Func,
    MIf as If,
    MEval as Eval,
    MShell as Shell,
    MCall as Call,
    MForeach as Foreach,
    MNot as Not,
)

from .lang import (
    MElement as Element,
    Makefile as File,
    MAppend as Append,
    MAssignment as Assignment,
    MAssignments as Assignments,
    MCommand as Command,
    MComment as Comment,
    MSet as Set,
    MSetImmediate as SetImmediate,
    MSetDefault as SetDefault,
    MRule as Rule,
    MPhony as Phony,
    MInclude as Include,
    MShellCommand as ShellCommand,
    MDefine as Define,
    MIfDef as IfDef,
    MIfNDef as IfNDef,
    MIfEq as IfEq,
    MIfNEq as IfNEq,
    MExprLine as ExprLine,
)

# Convenience constants
true = Const.true()
false = Const.false()
null = Null()


def all(*vars: Var) -> Expr:
    """
    Logical AND over a sequence of Var.
    all(a, b, c) becomes a & b & c, starting from true.
    """
    result: Expr = true
    for var in vars:
        result &= var
    return result


def any(*vars: Var) -> Expr:
    """
    Logical OR over a sequence of Var.
    any(a, b, c) becomes a | b | c, starting from false.
    """
    result: Expr = false
    for var in vars:
        result |= var
    return result


__all__ = [
    "Expr",
    "Const",
    "Var",
    "Arg",
    "Add",
    "And",
    "Or",
    "Func",
    "If",
    "Eval",
    "Shell",
    "Call",
    "Foreach",
    "Not",

    # expression API
    "true",
    "false",
    "null",
    "all",
    "any",

    # file / structure API
    "Element",
    "File",
    "Append",
    "Assignment",
    "Assignments",
    "Command",
    "Comment",
    "Set",
    "SetImmediate",
    "SetDefault",
    "Rule",
    "Phony",
    "Include",
    "ShellCommand",
    "Define",
    "If",
    "IfDef",
    "IfNDef",
    "IfEq",
    "IfNEq",
    "ExprLine",
]
