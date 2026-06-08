"""Expression algebra: simplification rules, equality, coercion, structure.

Most assertions use structural equality (==), which is independent of each
class's __str__ formatting.
"""
import pytest


# ── Boolean simplification ────────────────────────────────────────────────────

def test_idempotent_and_or(abc):
    A, B, C = abc
    assert (A & A) == A
    assert (A | A) == A

def test_bool_absorption_constants(abc, lang):
    A, _, _ = abc
    assert (A & lang.Bool.true()) == A
    assert (A | lang.Bool.false()) == A
    assert (A & lang.Bool.false()) == lang.Bool.false()
    assert (A | lang.Bool.true()) == lang.Bool.true()

def test_contradiction_and_tautology(abc, lang):
    A, _, _ = abc
    assert (A & ~A) == lang.Bool.false()
    assert (A | ~A) == lang.Bool.true()

def test_double_negation(abc):
    A, _, _ = abc
    assert ~~A == A

def test_de_morgan(abc):
    A, B, _ = abc
    assert ~(A & B) == (~A | ~B)
    assert ~(A | B) == (~A & ~B)

def test_absorption(abc):
    A, B, _ = abc
    assert (A & (A | B)) == A
    assert (A | (A & B)) == A

def test_and_or_are_commutative_via_sorting(abc):
    A, B, _ = abc
    assert (A & B) == (B & A)
    assert (A | B) == (B | A)

def test_nested_flatten_dedup(abc):
    A, B, C = abc
    # duplicate term collapses
    assert ((A & B) & A) == (A & B)
    assert ((A | B) | A) == (A | B)


# ── Arithmetic simplification ─────────────────────────────────────────────────

def test_constant_folding(lang):
    Int = lang.Int
    assert (Int(2) + Int(3)) == Int(5)
    assert (Int(6) / Int(2)) == Int(3)
    assert (Int(2) * Int(3)) == Int(6)

def test_coefficient_merge(lang):
    x = lang.Name("x")
    assert (x + x) == (lang.Int(2) * x)
    assert (x + x + x) == (lang.Int(3) * x)
    assert ((lang.Int(2) * x) + (lang.Int(3) * x)) == (lang.Int(5) * x)

def test_sub_to_zero_and_identity(lang):
    x = lang.Name("x")
    assert (x - x) == lang.Int(0)
    assert (x - lang.Int(0)) == x

def test_mul_annihilation_and_identity(lang):
    x = lang.Name("x")
    assert (lang.Int(0) * x) == lang.Int(0)
    assert (lang.Int(1) * x) == x

def test_div_reduces_constant_factor(lang):
    x = lang.Name("x")
    assert ((lang.Int(4) * x) / lang.Int(2)) == (lang.Int(2) * x)

def test_div_by_one_and_zero_over_x(lang):
    x = lang.Name("x")
    assert (x / lang.Int(1)) == x
    assert (lang.Int(0) / x) == lang.Int(0)


# ── Null propagation (identity element) ───────────────────────────────────────

def test_null_is_identity(abc, lang):
    A, _, _ = abc
    null = lang.Null()
    assert (null | A) == A
    assert (A | null) == A
    assert (null & A) == A
    assert (null | null) == null

def test_invert_null_is_null(lang):
    null = lang.Null()
    assert (~null) is null


# ── Equality, hashing, structure ──────────────────────────────────────────────

def test_structural_equality(abc, lang):
    A, B, _ = abc
    assert lang.Name("x") == lang.Name("x")
    assert lang.Name("x") != lang.Name("y")
    assert lang.And(A, B) == lang.And(A, B)

def test_hashable_by_key(abc, lang):
    A, B, _ = abc
    # __hash__ added: expressions usable in sets/dicts, consistent with ==
    assert len({A, A, lang.Name("A")}) == 1
    assert (A & B) in {A & B}

def test_len_counts_nodes(abc):
    A, B, C = abc
    expr = (A & B) | (~C & A)
    assert len(expr) == len(list(_walk(expr)))

def _walk(e):
    yield e
    for child in e:
        yield from _walk(child)


# ── Coercion protocol ─────────────────────────────────────────────────────────

def test_const_coerce_wraps_and_passes_through(lang):
    assert lang.String.coerce("hi") == lang.String("hi")
    A = lang.Name("A")
    assert lang.String.coerce(A) is A        # existing expr passes through
    assert lang.Int.coerce(5) == lang.Int(5)

def test_name_coerce(lang):
    assert lang.Name.coerce("A") == lang.Name("A")
    A = lang.Name("A")
    assert lang.Name.coerce(A) is A
    with pytest.raises(TypeError):
        lang.Name.coerce(123)
