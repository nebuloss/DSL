"""Kconfig sublanguage: variables, options, blocks, choices, escaping."""
import pytest
import dsl.kconfig as k


# ── Variables / constants ─────────────────────────────────────────────────────

def test_kvar_normalization():
    assert str(k.KVar("my.flag-name")) == "MY_FLAG_NAME"
    assert str(k.KVar("BR2_FOO")) == "BR2_FOO"

@pytest.mark.parametrize("bad", ["", "  ", " 7", "7x", "9abc"])
def test_kvar_rejects_bad_names(bad):
    with pytest.raises(ValueError):
        k.KVar(bad)

def test_kvar_rejects_non_string():
    with pytest.raises(TypeError):
        k.KVar(123)

def test_constants():
    assert str(k.KBool(True)) == "y"
    assert str(k.KBool(False)) == "n"
    assert str(k.KBool("y")) == "y"
    assert str(k.KInt(42)) == "42"
    assert str(k.KHex(255)) == "0xFF"
    assert str(k.KHex("0xff")) == "0xFF"

def test_kbool_invalid_string():
    with pytest.raises(TypeError):
        k.KBool("maybe")


# ── Expressions + escaping ────────────────────────────────────────────────────

def test_kconfig_expressions():
    A, B = k.KVar("A"), k.KVar("B")
    assert str(A & B) == "A && B"
    assert str(A | B) == "A || B"
    assert str(~A) == "!A"
    assert str(~(A & B)) == "!A || !B"          # De Morgan
    # && binds tighter than ||: parens added around OR inside AND
    assert str((A | B) & k.KVar("C")) == "C && (A || B)"

def test_string_escaping():
    assert str(k.KString('a"b\\c')) == '"a\\"b\\\\c"'


# ── Options + builder ─────────────────────────────────────────────────────────

def test_option_bool_full():
    out = str(
        k.KOptionBool(k.KVar("MY_DRIVER"), "Enable")
        .add_depends(k.KVar("HAS_HW"))
        .add_selects(k.KVar("CORE"))
        .add_default(k.KBool.true(), when=k.KVar("BOARD"))
        .add_help("Line one.")
    )
    expected = (
        "config MY_DRIVER\n"
        "\tbool \"Enable\"\n"
        "\tdefault y if BOARD\n"
        "\tdepends on HAS_HW\n"
        "\tselect CORE\n"
        "\thelp\n"
        "\t\tLine one."
    )
    assert out == expected

def test_option_int_range():
    out = str(k.KOptionInt(k.KVar("N"), "Count").add_range(k.KInt(10), k.KInt(5000)).add_default(k.KInt(100)))
    assert out == "config N\n\tint \"Count\"\n\trange 10 5000\n\tdefault 100"

def test_menuconfig_keyword():
    out = str(k.KMenuConfig(k.KVar("SUB"), "Sub"))
    assert out.startswith("menuconfig SUB\n\tbool \"Sub\"")


# ── Coercion equivalence ──────────────────────────────────────────────────────

def test_option_coercion_equivalence():
    new = str(
        k.KOptionBool("MY_OPT", "P")
        .add_depends("HAS_HW").add_selects("CORE").add_default(k.KBool.true())
    )
    old = str(
        k.KOptionBool(k.KVar("MY_OPT"), "P")
        .add_depends(k.KVar("HAS_HW")).add_selects(k.KVar("CORE")).add_default(k.KBool.true())
    )
    assert new == old

def test_default_raw_value_coercion():
    assert str(k.KOptionString("PATH").add_default("/tmp")) == \
           str(k.KOptionString(k.KVar("PATH")).add_default(k.KString("/tmp")))
    assert str(k.KOptionInt("N").add_range(10, 5000).add_default(100)) == \
           str(k.KOptionInt(k.KVar("N")).add_range(k.KInt(10), k.KInt(5000)).add_default(k.KInt(100)))


# ── Blocks ────────────────────────────────────────────────────────────────────

def test_menu_block():
    out = str(k.KMenu("Title", k.KOptionBool("X", "P")))
    assert out.startswith('menu "Title"')
    assert out.endswith("endmenu")
    assert "config X" in out

def test_if_block_and_coercion():
    assert str(k.KIf("FOO", k.KComment("c"))) == str(k.KIf(k.KVar("FOO"), k.KComment("c")))
    assert str(k.KIf(k.KVar("FOO"), k.KComment("c"))).startswith("if FOO")

def test_choice_block():
    out = str(k.KChoice("Pick", k.KOptionBool("A", "a"), k.KOptionBool("B", "b")))
    assert out.startswith("choice")
    assert out.endswith("endchoice")
    assert 'bool "Pick"' in out
    assert "config A" in out and "config B" in out


# ── Source / comment ──────────────────────────────────────────────────────────

def test_source_and_comment():
    assert str(k.KSource("path/Kconfig")) == 'source "path/Kconfig"'
    assert str(k.KComment("visible")) == 'comment "visible"'
