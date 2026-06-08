"""Makefile sublanguage: variables, assignments, rules, conditionals, functions."""
import pytest
import dsl.make as m


# ── Variables / constants ─────────────────────────────────────────────────────

def test_variable_rendering():
    assert str(m.MVar("FOO")) == "$(FOO)"
    assert str(m.MArg(1)) == "$(1)"
    assert str(m.mTargetVar) == "$@"
    assert str(m.mFirstPrerequisiteVar) == "$<"
    assert str(m.MBool(True)) == "1"
    assert str(m.MBool(False)) == ""
    assert str(m.mNULL) == ""

def test_mvar_allows_dot_and_dash():
    assert str(m.MVar("gitlab.zeetim-x")) == "$(gitlab.zeetim-x)"

def test_marg_requires_int():
    with pytest.raises(TypeError):
        m.MArg("1")


# ── Expressions ───────────────────────────────────────────────────────────────

def test_make_expressions():
    A, B = m.MVar("A"), m.MVar("B")
    assert str(m.MAdd(m.MString("foo"), m.MString("bar"))) == "foo bar"
    assert str(A & B) == "$(and $(A),$(B))"
    assert str(A | B) == "$(or $(A),$(B))"
    assert str(~A) == "$(if $(A),,1)"
    assert str(m.any_of(A, B, m.MVar("C"))) == "$(or $(A),$(B),$(C))"


# ── Assignments + alignment ───────────────────────────────────────────────────

def test_assignment_operators():
    assert str(m.MSet(m.MVar("X"), m.MString("v"))) == "X = v"
    assert str(m.MSetImmediate(m.MVar("X"), m.MString("v"))) == "X := v"
    assert str(m.MSetDefault(m.MVar("X"), m.MString("v"))) == "X ?= v"
    assert str(m.MAppend(m.MVar("X"), m.MString("v"))) == "X += v"

def test_assignment_list_alignment():
    out = str(m.MAssignmentList(
        m.MSet(m.MVar("CC"), m.MString("gcc")),
        m.MSetDefault(m.MVar("CFLAGS"), m.MString("-O2")),
        m.MSetImmediate(m.MVar("BUILDDIR"), m.MString("build")),
    ))
    assert out == "CC       =  gcc\nCFLAGS   ?= -O2\nBUILDDIR := build"

def test_assignment_coercion_equivalence():
    assert str(m.MSet("CC", "gcc")) == str(m.MSet(m.MVar("CC"), m.MString("gcc")))


# ── Rules ─────────────────────────────────────────────────────────────────────

def test_rule_variants():
    assert str(m.MStaticRule(m.MString("a"), prereqs=m.MString("b"))) == "a: b"
    assert str(m.MIndependentRule(m.MString("a"), prereqs=m.MString("b"))) == "a:: b"
    assert str(m.MGroupedRule(m.MString("a"), prereqs=m.MString("b"))) == "a&: b"
    assert str(m.MStaticRule(m.MString("a"), prereqs=m.MString("b"), order_only=m.MString("c"))) == "a: b | c"

def test_rule_requires_targets():
    with pytest.raises(ValueError):
        m.MStaticRule(m.MString("  "))

def test_rule_coercion():
    assert str(m.MStaticRule("all", prereqs="main.o")) == "all: main.o"

def test_phony():
    assert str(m.MPhony(m.MString("all clean"))) == ".PHONY: all clean"

def test_recipe_block():
    out = str(m.MRecipe(
        m.MStaticRule(m.MString("all"), prereqs=m.MString("main.o")),
        m.MCommand("gcc", "-o", "app", "main.o", flags=m.MFlag.SILENT),
    ))
    assert out == "all: main.o\n\t@gcc -o app main.o"


# ── Comments / commands / escaping ────────────────────────────────────────────

def test_comment():
    assert str(m.MComment("hi")) == "# hi"
    assert str(m.MComment("")) == "#"

def test_command_quotes_unsafe_strings():
    # plain strings are shell-quoted when they contain unsafe chars
    assert str(m.MCommand("echo", "hello world")) == "echo 'hello world'"
    assert str(m.MCommand("echo", "a'b")) == "echo 'a'\"'\"'b'"

def test_command_mexpr_is_verbatim():
    # MExpr args are inserted as-is (not shell-quoted)
    assert str(m.MCommand("gcc", m.MVar("CFLAGS"), "-o", "app")) == "gcc $(CFLAGS) -o app"

def test_command_flags():
    assert str(m.MCommand("rm", "-f", "x", flags=m.MFlag.IGNORE_ERRORS | m.MFlag.SILENT)) == "-@rm -f x"

def test_command_requires_name():
    with pytest.raises(ValueError):
        m.MCommand("")


# ── Conditionals (tight blocks — regression) ──────────────────────────────────

def test_standalone_conditional_is_tight():
    out = str(m.MIfDef(m.MVar("REL"), m.MText("X=1"), m.MText("Y=2")))
    assert out == "ifdef REL\nX=1\nY=2\nendif"

def test_condition_list_is_tight():
    out = str(m.MConditionList(
        m.MIfDef(m.MVar("A"), m.MText("X=1")),
        m.MElse(m.MText("X=2")),
    ))
    assert out == "ifdef A\nX=1\nelse\nX=2\nendif"

def test_condition_chain_else_prefix():
    out = str(m.MConditionList(
        m.MIfDef(m.MVar("A"), m.MText("X=1")),
        m.MIfDef(m.MVar("B"), m.MText("X=2")),
        m.MElse(m.MText("X=3")),
    ))
    assert out == "ifdef A\nX=1\nelse ifdef B\nX=2\nelse\nX=3\nendif"

def test_ifeq():
    out = str(m.MIfEq(m.MVar("ARCH"), m.MString("arm"), m.MText("X=1")))
    assert out == "ifeq ($(ARCH),arm)\nX=1\nendif"

def test_conditional_coercion():
    assert str(m.MIfDef("REL", m.MText("X=1"))) == str(m.MIfDef(m.MVar("REL"), m.MText("X=1")))

def test_makefile_keeps_blank_margin_between_sections():
    out = str(m.Makefile(
        m.MComment("one"),
        m.MConditionList(m.MIfDef(m.MVar("A"), m.MText("X=1")), m.MElse(m.MText("X=2"))),
        m.MComment("two"),
    ))
    assert out == "# one\n\nifdef A\nX=1\nelse\nX=2\nendif\n\n# two"


# ── define block (bare name + tight — regression) ─────────────────────────────

def test_define_uses_bare_name_and_is_tight():
    out = str(m.MDefine(m.MVar("FOO"), m.MText("A := 1"), m.MText("B := 2")))
    assert out == "define FOO\nA := 1\nB := 2\nendef"


# ── Functions ─────────────────────────────────────────────────────────────────

def test_functions():
    assert str(m.MIfFunc(m.MVar("A"), m.MString("yes"), m.MString("no"))) == "$(if $(A),yes,no)"
    assert str(m.MIfFunc(m.MVar("A"), m.MString("yes"))) == "$(if $(A),yes)"
    assert str(m.MShellFunc(m.MString("uname -m"))) == "$(shell uname -m)"
    assert str(m.MEvalFunc(m.MString("x"))) == "$(eval x)"
    assert str(m.MCallFunc(m.MVar("fn"), m.MString("a1"))) == "$(call fn,a1)"
    assert str(m.MForeachFunc(m.MVar("f"), m.MVar("LIST"), m.MVar("f"))) == "$(foreach f,$(LIST),$(f))"

def test_callfunc_requires_mvar():
    with pytest.raises(TypeError):
        m.MCallFunc("fn")


# ── Include ───────────────────────────────────────────────────────────────────

def test_include_escapes_spaces():
    assert str(m.MInclude("a.mk", "b c.mk")) == "include a.mk b\\ c.mk"
