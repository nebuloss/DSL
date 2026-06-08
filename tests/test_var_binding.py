"""Language binding, registration, validation, and generic-arg machinery."""
import pytest

from dsl import Language, VarBool, VarName, VarNot, VarAnd, VarOr, VarNull
from dsl.generic_args import GenericArgsMixin


def test_registration_populates_language():
    lng = Language("reg")

    class B(VarBool[lng]): ...
    class N(VarName[lng]): ...
    class Nt(VarNot[lng]): ...
    class An(VarAnd[lng]): ...
    class Or_(VarOr[lng]): ...
    class Nl(VarNull[lng]): ...

    assert lng.types.Bool is B
    assert lng.types.Name is N
    assert lng.ops.Not is Nt
    assert lng.ops.And is An
    assert lng.ops.Or is Or_
    assert lng.types.Null is Nl
    lng.validate()  # should not raise


def test_validate_reports_missing():
    lng = Language("incomplete")

    class B(VarBool[lng]): ...
    # Name / Not / And / Or missing

    with pytest.raises(RuntimeError) as exc:
        lng.validate()
    msg = str(exc.value)
    for missing in ("types.Name", "ops.Not", "ops.And", "ops.Or"):
        assert missing in msg


def test_cross_language_combination_rejected():
    l1, l2 = Language("l1"), Language("l2")

    class N1(VarName[l1]):
        def __str__(self): return self.name
    class B1(VarBool[l1]): ...
    class Not1(VarNot[l1]): ...
    class And1(VarAnd[l1]): ...
    class Or1(VarOr[l1]): ...

    class N2(VarName[l2]):
        def __str__(self): return self.name
    class B2(VarBool[l2]): ...
    class Not2(VarNot[l2]): ...
    class And2(VarAnd[l2]): ...
    class Or2(VarOr[l2]): ...

    with pytest.raises(TypeError):
        N1("a") & N2("b")


def test_varnull_must_be_subclassed():
    with pytest.raises(TypeError):
        VarNull()


def test_varnull_singleton_per_language():
    lng = Language("nulltest")

    class Nl(VarNull[lng]):
        def __str__(self): return ""

    assert Nl() is Nl()


def test_generic_args_specialization_is_cached_and_real_subclass():
    class Base(GenericArgsMixin):
        pass

    A = Base["="]
    B = Base["="]
    C = Base[":="]
    assert A is B            # cached
    assert A is not C
    assert issubclass(A, Base)
    assert A.get_arg(0) == "="


def test_get_arg_errors():
    class Base(GenericArgsMixin):
        pass

    with pytest.raises(TypeError):
        Base.get_arg(0)         # not parametrized

    with pytest.raises(IndexError):
        Base["x"].get_arg(5)    # out of range
