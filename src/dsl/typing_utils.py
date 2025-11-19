# dsl/typing_utils.py

from typing import Any, TypeVar, Type, get_args

T = TypeVar("T")


def resolve_generic_type_arg(
    obj: Any,
    *,
    index: int,
    expected: Type[T],
) -> Type[T]:
    """
    Resolve generic type argument at position `index`.

    - Walks the MRO and inspects __orig_bases__ on each base.
    - For each generic origin, it looks at args[index].
    - Returns the first argument that is a subclass of `expected`.
    - If no generic origin exists at all, returns `expected`.
    - If at least one origin exists but none matches `expected`, raises.
    """

    saw_any_origin = False

    for base in type(obj).mro():
        for gb in getattr(base, "__orig_bases__", ()):
            args = get_args(gb)
            if not args:
                continue

            if len(args) <= index:
                continue

            saw_any_origin = True

            cand = args[index]
            if isinstance(cand, type) and issubclass(cand, expected):
                return cand  # type: ignore[return-value]

    if not saw_any_origin:
        # No generic info at all for this object: fall back
        return expected

    raise TypeError(
        f"Could not resolve generic parameter {index} as subclass of "
        f"{expected.__name__} for {type(obj).__name__}"
    )
