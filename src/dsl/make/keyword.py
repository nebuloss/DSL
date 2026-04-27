"""
Makefile keyword nodes (always at column 0).

MKeyword uses GenericArgsMixin so the keyword string is part of the class:

    MKeyword["ifdef"]  — produces a class whose instances render "ifdef …"

MKeyword inherits FixedNode, so it always renders at level 0 regardless of
how deeply nested it is inside other containers.  This is required because
Make conditionals (ifdef/endif/else) must not be indented.

MConditionKeyword adds with_else_prefix() which transforms the keyword into
its "else" form:  ifdef → else ifdef,  ifeq → else ifeq,  else → else.
This is used by MConditionList to merge separate condition blocks into a
single if/else ifdef/else/endif chain without duplicating endif.

Singletons MELSE_KEYWORD, MENDIF_KEYWORD, MENDEF_KEYWORD are module-level
instances reused across all generated output.
"""
from typing import List, cast

from dsl.container import FixedNode
from dsl.content import WordlistNode
from dsl.generic_args import GenericArgsMixin
from dsl.make.var import MExpr, MVar


class MKeyword(GenericArgsMixin,FixedNode[WordlistNode]):
    """
    Simple fixed keyword node.
    The text passed here is the full line content.
    """

    def __init__(self,*args:str) -> None:
        # Extract the keyword from the first token of the text
        self._name=self.get_arg(0)
        self._args=args
        FixedNode.__init__(self,WordlistNode(self._name,*args), level=0)

    @property
    def name(self) -> str:
        """
        Keyword name, usually the first token of the line
        (for example "ifdef", "ifeq", "include", "define", "else").
        """
        return self._name
    
    @property
    def args(self)->List[str]:
        return self._args
    
class MSingleKeyword(MKeyword):
    def __init__(self):
        super().__init__()


class MDefineKeyword(MKeyword["define"]):
    """
    "define VAR" keyword. Accepts exactly one MVar argument.
    """

    def __init__(self, var: MVar) -> None:
        super().__init__(str(var))

    @staticmethod
    def format_args(*args: MExpr) -> str:
        if len(args) != 1:
            raise ValueError("define accepts exactly one argument")
        val = args[0]
        if not isinstance(val, MVar):
            raise TypeError("Expecting MVar for define argument")
        return cast(MVar, val).name


class MIncludeKeyword(MKeyword["include"]):
    """
    Makefile include line.

    - Escapes spaces in each path ("foo bar" becomes "foo\\ bar")
    - Supports multiple paths, for example:
      MIncludeKeyword("a.mk", "b mk") -> "include a.mk b\\ mk"
    """

    def __init__(self, *args: MExpr) -> None:
        super().__init__(*(self.format_args(arg) for arg in args))

    @staticmethod
    def format_args(*args: MExpr) -> str:
        return " ".join(str(arg).replace(" ", r"\ ") for arg in args)


class MConditionKeyword(MKeyword):
    """
    Base class for conditional directives: if, ifdef, ifndef, ifeq, ifneq, else, and else-prefixed variants.
    """

    def with_else_prefix(self) -> "MConditionKeyword":
        """
        Return a new condition keyword representing the "else" form
        of this condition.

        Examples:
        - ifdef VAR -> else ifdef VAR
        - ifeq (a,b) -> else ifeq (a,b)
        - else -> else
        """
        # Use the first token as the directive name, this matches Makefile syntax
        name = self.name

        # If the directive is already "else", we keep it as is
        if name == "else":
            new_keyword = "else"
        else:
            new_keyword = "else " + name

        return MConditionKeyword[new_keyword](*self.args)

class MSingleConditionKeyword(MConditionKeyword):
    def __init__(self,cond: MExpr):
        if isinstance(cond, MVar):
            arg=cond.name
        else:
            arg=str(cond)
        super().__init__(arg)

class MDoubleConditionKeyword(MConditionKeyword):
    def __init__(self, left: MExpr, right: MExpr):
        arg="(" + ",".join(str(x) for x in (left, right)) + ")"
        super().__init__(arg)


MELSE_KEYWORD=MConditionKeyword["else"]()
MENDIF_KEYWORD=MSingleKeyword["endif"]()
MENDEF_KEYWORD=MSingleKeyword["endef"]()

MIfKeyword=MSingleConditionKeyword["if"]
MIfDefKeyword=MSingleConditionKeyword["ifdef"]
MIfNDefKeyword=MSingleConditionKeyword["ifndef"]

MIfEqKeyword=MDoubleConditionKeyword["ifeq"]
MIfNEqKeyword=MDoubleConditionKeyword["ifneq"]
