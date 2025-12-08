from __future__ import annotations

from typing import Any


class GenericArgsMixin:
    """Mixin that binds type arguments to the specialized class.

    Example:
        class MyContainer(GenericArgsMixin):
            pass

        C = MyContainer[int, str]
        assert C.get_arg(0) is int
        assert C.get_arg(1) is str
    """

    _type_args: tuple[Any, ...] = ()
    _specializations: dict[tuple[Any, ...], type] = {}

    @classmethod
    def __class_getitem__(cls, params: Any) -> type:
        # Normalize to a tuple of args
        if not isinstance(params, tuple):
            params = (params,)

        # Per base class, keep its own cache
        if "_specializations" not in cls.__dict__:
            cls._specializations = {}

        # Return cached specialization if it already exists
        if params in cls._specializations:
            return cls._specializations[params]

        # Create a new subclass that remembers its type arguments
        name = f"{cls.__name__}[{', '.join(_type_repr(p) for p in params)}]"
        subclass = type(name, (cls,), {"_type_args": params})

        cls._specializations[params] = subclass
        return subclass

    @classmethod
    def get_arg(cls, index: int = 0, *, recursive: bool = False) -> Any:
        """Return the generic argument at the given index.

        If recursive is False (default), only the class itself is inspected.
        If recursive is True, the method walks the MRO until it finds a class
        with _type_args set and returns from there.
        """
        if not recursive:
            if not cls._type_args:
                raise TypeError(f"{cls.__name__} is not parametrized with type arguments")
            try:
                return cls._type_args[index]
            except IndexError:
                raise IndexError(
                    f"{cls.__name__} only has {len(cls._type_args)} type argument(s)"
                ) from None

        # recursive lookup: walk the MRO, find the first parametrised class
        for c in cls.__mro__:
            args = getattr(c, "_type_args", ())
            if not args:
                continue
            try:
                return args[index]
            except IndexError:
                raise IndexError(
                    f"{c.__name__} only has {len(args)} type argument(s)"
                ) from None

        raise TypeError(
            f"{cls.__name__} is not parametrized with type arguments "
            "in its MRO"
        )


def _type_repr(t: Any) -> str:
    """Human readable name used in the generated class name."""
    return getattr(t, "__name__", repr(t))
