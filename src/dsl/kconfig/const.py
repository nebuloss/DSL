from abc import abstractmethod
from typing import Any, Union

from dsl.kconfig.var import KconfigOps
from dsl.var import VarConst

class KConst(VarConst[KconfigOps]):
    """
    Abstract base Kconfig constant.

    Subclasses (KConstBool, KConstInt, KConstString, KConstHex) perform
    validation and normalisation. This class should not be instantiated
    directly.
    """

    @classmethod
    @abstractmethod
    def typename(cls) -> str:
        raise NotImplementedError
    
    @staticmethod
    def true() -> "KConstBool":
        return KConstBool(True)

    @staticmethod
    def false() -> "KConstBool":
        return KConstBool(False)

class KConstBool(KConst):

    def __init__(self, val: Union[str, bool, int]):
        if isinstance(val, bool):
            v = val
        elif isinstance(val, int):
            v = bool(val)
        elif isinstance(val, str):
            s = val.strip().lower()
            if s == "y":
                v = True
            elif s == "n":
                v = False
            else:
                raise TypeError("Bool constant string must be 'y' or 'n'")
        else:
            raise TypeError("Bool constant must be bool, int, or 'y'/'n'")
        super().__init__(v)

    def __str__(self) -> str:
        return "y" if bool(self.val) else "n"

    @classmethod
    def typename(cls) -> str:
        return "bool"


class KConstInt(KConst):

    def __init__(self, val: Union[int, str, bool]):
        if isinstance(val, bool):
            v = int(val)
        elif isinstance(val, int):
            v = val
        elif isinstance(val, str):
            s = val.strip()
            if not s or not s.isdigit():
                raise TypeError("Int constant string must be a decimal integer")
            v = int(s)
        else:
            raise TypeError("Int constant must be int, bool, or decimal string")
        super().__init__(v)

    def __str__(self) -> str:
        return str(int(self.val))

    @classmethod
    def typename(cls) -> str:
        return "int"


class KConstString(KConst):

    def __init__(self, val: Any):
        super().__init__(str(val))

    @staticmethod
    def _escape_string(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def __str__(self) -> str:
        return f"\"{self._escape_string(str(self.val))}\""

    @classmethod
    def typename(cls) -> str:
        return "string"


class KConstHex(KConst):

    def __init__(self, val: Union[int, str, bool]):
        if isinstance(val, bool):
            v = int(val)
        elif isinstance(val, int):
            v = val
        elif isinstance(val, str):
            s = val.strip()
            try:
                v = int(s, 16)
            except ValueError:
                raise TypeError("Hex constant string must be a valid hex literal")
        else:
            raise TypeError("Hex constant must be int, bool, or hex string")
        super().__init__(v)

    def __str__(self) -> str:
        return f"0x{int(self.val):X}"

    @classmethod
    def typename(cls) -> str:
        return "hex"
