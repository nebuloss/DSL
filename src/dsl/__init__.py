# dsl/__init__.py

from .var import (
    LanguageOps,
    VarExpr,
    VarUnaryOp,
    VarBinaryOp,
    VarConst,
    VarName,
    VarNull,
    VarNot,
    VarAnd,
    VarOr,
    VarAdd,
    VarSub,
    VarMul,
    VarDiv,
)

from .node import (
    Node,
    Line,
)

from .content import (
    NullNode,
    NULL_NODE,
    GenericTextNode,
    TextNode,
    FixedTextNode,
    BlankLine,
)

from .container import (
    ContainerNode,
    SimpleNodeStack,
    Stack,
    Block,
    WordAlignedStack,
)

from . import kconfig
from . import make

# Optional alias for backward compatibility
Text = TextNode


__all__ = [
    # var language core
    "LanguageOps",
    "VarExpr",
    "VarUnaryOp",
    "VarBinaryOp",
    "VarConst",
    "VarName",
    "VarNull",
    "VarNot",
    "VarAnd",
    "VarOr",
    "VarAdd",
    "VarSub",
    "VarMul",
    "VarDiv",

    # node and content
    "Node",
    "Line",
    "NullNode",
    "NULL_NODE",
    "GenericTextNode",
    "TextNode",
    "FixedTextNode",
    "BlankLine",

    # containers
    "ContainerNode",
    "SimpleNodeStack",
    "Stack",
    "WordAlignedStack",
    "Block",

    # legacy alias
    "Text",

    # sublanguages
    "kconfig",
    "make",
]
