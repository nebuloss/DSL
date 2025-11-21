from abc import ABC, abstractmethod
from typing import Iterable, List, Self, Union, cast
from dsl.container import DelimitedNodeBlock, NodeBlock, SimpleNodeStack
from dsl.content import FixedTextNode, TextNode
from dsl.make.core import MLine, MElement, Makefile
from dsl.make.var import MExpr, MVar
    
class MKeyword(FixedTextNode):
    def __init__(self, name: str) -> None:
        # Extract the keyword name using lsplit(max=1)
        parts = name.split(" ", maxsplit=1)
        self._name = parts[0] if parts else ""

        # Store the full text in the FixedTextNode
        super().__init__(name, level=0)

    @property
    def name(self) -> str:
        return self._name


class MArgsKeyword(MKeyword, ABC):
    def __init__(self, name: str, *args: MExpr) -> None:
        # Store arguments as a list to match the return type
        self._args: List[MExpr] = list(args)

        # Build full text once, with arguments formatted
        if args:
            full_text = name + " " + self.format_args(*args)
        else:
            full_text = name

        # This will call MKeyword.__init__, which will also set self._name
        super().__init__(full_text)

    @staticmethod
    @abstractmethod
    def format_args(*args: MExpr) -> str:
        ...

    @property
    def args(self) -> List[MExpr]:
        return self._args

class MDefineKeyword(MArgsKeyword):
    def __init__(self, var:MVar):
        super().__init__("define",var)

    @staticmethod
    def format_args(*args):
        if len(args)!=1:
            raise ValueError("define accept only one argument")
        val=args[0]
        if not isinstance(val,MVar):
            raise TypeError("Expecting MVar for define argument")
        return cast(MVar,val).name

MEndefKeyword=MKeyword("endef")

class MIncludeKeyword(MArgsKeyword):
    def __init__(self,*args: MExpr):
        super().__init__("include", *args)

    @staticmethod
    def format_args(*args:MExpr):
        return " ".join(*args)

class MConditionKeyword(MArgsKeyword):
    def __init__(self, keyword:str ,*args:MExpr):
        if not keyword:
            raise ValueError("empty condition statement not allowed")
        
        super().__init__(keyword,*args)
    
    def with_else_prefix(self)->"MConditionKeyword":
        name=self.name
        if name!="else":
            name="else "+name
        return MConditionKeyword(name,*self.args)

MEndifKeyword=MKeyword("endif")

class MVarConditionKeyword(MConditionKeyword):
    def __init__(self, keyword, var:MVar):
        if not isinstance(var,MVar):
            raise TypeError("Expexting MVar for single arg condition!")
        super().__init__(keyword, var)

    @staticmethod
    def format_args(*args):
        return cast(MVar,args[0]).name
    
class MExprConditionKeyword(MConditionKeyword):
    def __init__(self, keyword, a:MExpr, b:MExpr):
        super().__init__(keyword, a,b)

    @staticmethod
    def format_args(*args):
        return "("+",".join(args)+")"


class MIfKeyword(MVarConditionKeyword):
    def __init__(self, var:MVar):
        super().__init__("if", var)
