"""
GenericArgsMixin — compile-time type argument binding.

Problem: we want to write  MAssignment["="]  and get back a real class
whose instances "know" their operator is "=", without passing it at
construction time.  Standard Python generics (typing.Generic) keep type
arguments only as metadata; they are erased at runtime and do not affect
isinstance() or __init_subclass__ hooks.

Solution: __class_getitem__ creates an actual subclass instead of a plain
GenericAlias.  The subclass stores the arguments in _type_args and is
cached so the same specialisation is always the same object.

Why a real subclass?
  - isinstance(x, MSet) works correctly.
  - __init_subclass__ fires on further subclasses, allowing auto-registration
    of operators and types into Language (see var.py).
  - get_arg() is just a class attribute lookup, no runtime overhead.

Usage pattern:
    class MyBase(GenericArgsMixin):
        def __init__(self):
            op = self.get_arg(0)   # retrieves the first type argument

    Specialised = MyBase["="]      # real subclass with _type_args = ("=",)
    instance    = Specialised()    # get_arg(0) returns "="
"""
from __future__ import annotations

from typing import Any


class GenericArgsMixin:

    _type_args: tuple[Any, ...] = ()
    # Per-class cache so different base classes don't share specialisations.
    _specializations: dict[tuple[Any, ...], type] = {}

    @classmethod
    def __class_getitem__(cls, params: Any) -> type:
        if not isinstance(params, tuple):
            params = (params,)

        # Each subclass gets its own cache dict (not inherited from the base).
        if "_specializations" not in cls.__dict__:
            cls._specializations = {}

        if params in cls._specializations:
            return cls._specializations[params]

        # Build a new class whose name encodes the arguments for readability
        # in tracebacks and repr().  _type_args is in __dict__ so the
        # __init_subclass__ guard  `"_type_args" in cls.__dict__`  can
        # distinguish this intermediate class from a user-defined subclass.
        name = f"{cls.__name__}[{', '.join(_type_repr(p) for p in params)}]"
        subclass = type(name, (cls,), {"_type_args": params})

        cls._specializations[params] = subclass
        return subclass

    @classmethod
    def get_arg(cls, index: int = 0) -> Any:
        """Return the type argument at position *index*."""
        if not cls._type_args:
            raise TypeError(f"{cls.__name__} is not parametrized with type arguments")
        try:
            return cls._type_args[index]
        except IndexError:
            raise IndexError(
                f"{cls.__name__} only has {len(cls._type_args)} type argument(s)"
            ) from None


def _type_repr(t: Any) -> str:
    return getattr(t, "__name__", repr(t))
