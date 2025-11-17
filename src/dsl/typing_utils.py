# typing_utils.py
from typing import Any, TypeVar, Type, get_args

TExpected = TypeVar("TExpected")

def resolve_generic_type_arg(
    obj: Any,
    *,
    index: int,
    expected: Type[TExpected],
) -> Type[TExpected]:
    """
    Resolve generic type argument at position `index` that is a
    subclass of `expected`.

    Looks at instance __orig_class__ then walks the MRO and inspects
    each base's __orig_bases__.
    """
#    print(f"resolve type for {type(obj)} index {index} expected {expected}")
    # Instance-level generic: foo: Foo[Bar] = Foo(...)
    orig = getattr(obj, "__orig_class__", None)
    if orig is not None:
        args = get_args(orig)
#        print(args)
        if len(args) > index:
            cand = args[index]
            if isinstance(cand, type) and issubclass(cand, expected):
                return cand  # type: ignore[return-value]

    # Walk the MRO and inspect __orig_bases__ of each base
    for base in type(obj).mro():
        for gb in getattr(base, "__orig_bases__", ()):
            args = get_args(gb)
#            print(args)
            if len(args) > index:
                cand = args[index]
                if isinstance(cand, type) and issubclass(cand, expected):
                    return cand  # type: ignore[return-value]

    raise TypeError(
        f"Could not resolve generic parameter {index} as subclass of "
        f"{expected.__name__} for {type(obj).__name__}"
    )
