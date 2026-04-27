# DSL — Makefile & Kconfig generator

A Python library for programmatically generating **Makefile** and **Kconfig** source files.  
Build a tree of nodes in Python, call `str(root)` to get the rendered text.

---

## Why

Writing large Makefiles or Kconfig trees by hand is error-prone and hard to
compose.  This library lets you build them from typed Python objects, with:

- Correct indentation handled automatically.
- Boolean and arithmetic expressions that simplify themselves (De Morgan, constant folding, …).
- Column-aligned assignment lists with no manual padding.
- Reusable, composable fragments.

---

## Architecture

The library has three layers:

```
┌──────────────────────────────────────┐
│  Sublanguages                        │
│   dsl.make    — Makefile nodes       │
│   dsl.kconfig — Kconfig nodes        │
├──────────────────────────────────────┤
│  Expression algebra  (dsl.var)       │
│   Language · VarExpr · VarBool …     │
│   Operators: And · Or · Not · Add …  │
├──────────────────────────────────────┤
│  Node / render system  (dsl.node …)  │
│   Node · Line · NodeBlock …          │
└──────────────────────────────────────┘
```

### Layer 1 — Node / render system

Every piece of output is a `Node`.  Nodes form a tree; rendering is done by:

```python
str(node)          # renders the whole tree to a string
node.render(level) # yields Line(indent_level, text) objects
```

`Line` keeps the indentation level separate from the text so parent containers
can shift entire subtrees without string manipulation.

Key node types from `dsl`:

| Class | Role |
|---|---|
| `TextNode` | List of strings, each on its own line |
| `WordlistNode` | Words joined into a single line |
| `WordAlignedStack` | Column-aligns rows of words |
| `NodeStack` | Children separated by an optional margin node |
| `NodeBlock` | Header node + indented children |
| `DelimitedNodeBlock` | NodeBlock with a closing node (endif, endmenu…) |
| `IndentedNode` | Shifts a child's level by a relative offset |
| `NullNode` | Renders to nothing; used as a no-op default |

### Layer 2 — Expression algebra

`VarExpr` is the base for all expressions.  Python operators are overloaded:

| Python | Meaning |
|---|---|
| `a \| b` | logical OR |
| `a & b` | logical AND |
| `~a` | logical NOT |
| `a + b` | addition / concatenation |
| `a - b` | subtraction |
| `a * b` | multiplication |
| `a / b` | division |

Expressions **simplify themselves eagerly** on every operation:

```python
A & A        # → A          (idempotent)
A & ~A       # → false      (contradiction)
A | ~A       # → true       (tautology)
~(A & B)     # → ~A | ~B   (De Morgan)
2*x + 3*x   # → 5*x        (coefficient merge)
DInt(6)/DInt(2)  # → DInt(3)  (constant folding)
```

### Layer 3 — Language binding

A `Language` is a registry that maps abstract roles (`Bool`, `Int`, `Not`, …)
to concrete classes.  Binding happens automatically when you subclass using
the `[language]` syntax:

```python
my_lang = Language("my_lang")

class MyBool(VarBool[my_lang]):   # registers my_lang.types.Bool = MyBool
    def __str__(self): return "true" if self.value else "false"

class MyAnd(VarAnd[my_lang]):     # registers my_lang.ops.And = MyAnd
    def __str__(self): return f"{self.left} AND {self.right}"
```

This pattern uses `GenericArgsMixin` under the hood: `VarBool[my_lang]` creates
a real intermediate subclass, and `MyBool` subclassing it triggers
`VarBool.__init_subclass__`, which performs the registration.

---

## Installation

```bash
pip install -e .
```

Requires Python ≥ 3.12 (uses PEP 695 generic syntax).

---

## Quick start — Makefile

```python
from dsl import make as mk

mf = mk.Makefile(
    mk.MAssignmentList(
        mk.MSet(mk.MVar("CC"),     mk.MString("gcc")),
        mk.MSetDefault(mk.MVar("CFLAGS"), mk.MString("-O2 -Wall")),
    ),
    mk.MPhony(mk.MString("all clean")),
    mk.MRecipe(
        mk.MStaticRule(mk.MString("all"), prereqs=mk.MString("main.o")),
        mk.MCommand("$(CC)", "$(CFLAGS)", "-o", "app", "main.o",
                    flags=mk.MFlag.SILENT),
    ),
    mk.MRecipe(
        mk.MStaticRule(mk.MString("clean")),
        mk.MCommand("rm", "-f", "app", "*.o", flags=mk.MFlag.SILENT),
    ),
)

print(mf)
```

Output:
```makefile
CC     =  gcc
CFLAGS ?= -O2 -Wall

.PHONY: all clean

all: main.o
	@gcc $(CFLAGS) -o app main.o

clean:
	@rm -f app *.o
```

---

## Quick start — Kconfig

```python
from dsl import kconfig as kc

cfg = kc.KConfig(
    kc.KMenu("Driver options",
        kc.KOptionBool(kc.KVar("MY_DRIVER"), "Enable my driver")
            .add_depends(kc.KVar("HAS_HW"))
            .add_selects(kc.KVar("DRIVER_CORE"))
            .add_default(kc.KBool.true(), when=kc.KVar("BOARD_DEFAULT"))
            .add_help("Enable the driver subsystem."),
        kc.KOptionInt(kc.KVar("TIMEOUT_MS"), "Timeout in milliseconds")
            .add_range(kc.KInt(10), kc.KInt(5000))
            .add_default(kc.KInt(100)),
    )
)

print(cfg)
```

Output:
```kconfig
menu "Driver options"

	config MY_DRIVER
		bool "Enable my driver"
		default y if BOARD_DEFAULT
		default n
		depends on HAS_HW
		select DRIVER_CORE
		help
			Enable the driver subsystem.

	config TIMEOUT_MS
		int "Timeout in milliseconds"
		range 10 5000
		default 100

endmenu
```

---

## Make reference

### Variables

| Class | Renders as |
|---|---|
| `MVar("FOO")` | `$(FOO)` |
| `MString("text")` | `text` |
| `MBool(True)` | `1` |
| `MBool(False)` | `` (empty) |
| `MArg(1)` | `$(1)` |
| `mTargetVar` | `$@` |
| `mFirstPrerequisiteVar` | `$<` |
| `mPrerequisitesVar` | `$^` |
| `mNULL` | `` (empty, identity for MAdd) |

### Expressions

```python
mk.MAdd(mk.MString("foo"), mk.MString("bar"))  # → "foo bar"
mk.MVar("A") & mk.MVar("B")                    # → $(and $(A),$(B))
mk.MVar("A") | mk.MVar("B")                    # → $(or $(A),$(B))
~mk.MVar("A")                                  # → $(if $(A),,1)
mk.any_of(a, b, c)                             # → $(or $(a),$(b),$(c))
mk.all_of(a, b, c)                             # → $(and $(a),$(b),$(c))
```

### Assignments

```python
mk.MSet(mk.MVar("X"), mk.MString("val"))         # X = val
mk.MSetImmediate(mk.MVar("X"), mk.MString("val"))# X := val
mk.MSetDefault(mk.MVar("X"), mk.MString("val"))  # X ?= val
mk.MAppend(mk.MVar("X"), mk.MString("val"))      # X += val
```

Wrap several assignments in `MAssignmentList` for automatic column alignment:

```python
mk.MAssignmentList(
    mk.MSet(mk.MVar("CC"),    mk.MString("gcc")),
    mk.MSetDefault(mk.MVar("CFLAGS"), mk.MString("-O2")),
    mk.MSetImmediate(mk.MVar("BUILDDIR"), mk.MString("build")),
)
# CC       =  gcc
# CFLAGS   ?= -O2
# BUILDDIR := build
```

### Rules

```python
mk.MStaticRule(targets, prereqs=None, order_only=None)  # targets: prereqs
mk.MIndependentRule(targets, prereqs=None)               # targets:: prereqs
mk.MGroupedRule(targets, prereqs=None)                   # targets&: prereqs
mk.MPhony(mk.MString("all clean"))                       # .PHONY: all clean
```

Wrap a rule in `MRecipe` to add recipe commands:

```python
mk.MRecipe(
    mk.MStaticRule(mk.MString("foo"), prereqs=mk.MString("bar")),
    mk.MCommand("gcc", "-o", mk.mTargetVar, mk.mFirstPrerequisiteVar),
    mk.MText("@echo done"),
)
```

### Command flags

`MFlag` is a bitmask; flags can be combined with `|`:

| Flag | Prefix | Effect |
|---|---|---|
| `MFlag.NONE` | | default |
| `MFlag.SILENT` | `@` | suppress echoing |
| `MFlag.IGNORE_ERRORS` | `-` | continue on non-zero exit |
| `MFlag.ALWAYS` | `+` | run even with `--dry-run` |

### Conditionals

```python
mk.MIfDef(mk.MVar("DEBUG"), body...)    # ifdef DEBUG … endif
mk.MIfNDef(mk.MVar("RELEASE"), body...) # ifndef RELEASE … endif
mk.MIf(mk.MVar("FLAG"), body...)        # if FLAG … endif
mk.MIfEq(mk.MVar("ARCH"), mk.MString("arm"), body...)  # ifeq ($(ARCH),arm) … endif
mk.MIfNEq(a, b, body...)               # ifneq …
```

Chain conditions with `MConditionList`:

```python
mk.MConditionList(
    mk.MIfDef(mk.MVar("RELEASE"), ...),
    mk.MIfDef(mk.MVar("DEBUG"),   ...),
    mk.MElse(...),
)
# ifdef RELEASE
#   …
# else ifdef DEBUG
#   …
# else
#   …
# endif
```

### Functions

```python
mk.MIfFunc(cond, then, otherwise)       # $(if cond,then,else)
mk.MShellFunc(mk.MString("uname -m"))   # $(shell uname -m)
mk.MCallFunc(mk.MVar("myfunc"), arg1)   # $(call myfunc,arg1)
mk.MForeachFunc(mk.MVar("f"), items, body)  # $(foreach f,items,body)
mk.MEvalFunc(mk.MString("$(X): $(Y)"))  # $(eval …)
```

### Other elements

```python
mk.MComment("Generated file — do not edit")  # # Generated file …
mk.MText("raw line")
mk.MInclude("config.mk", "rules.mk")
```

---

## Kconfig reference

### Variables and constants

| Class | Renders as |
|---|---|
| `KVar("MY_OPT")` | `MY_OPT` |
| `KBool(True)` / `KBool("y")` | `y` |
| `KBool(False)` / `KBool("n")` | `n` |
| `KInt(42)` | `42` |
| `KHex(0xFF)` / `KHex("0xFF")` | `0xFF` |
| `KString("text")` | `"text"` |
| `KNull()` / `kNULL` | `` (empty, identity element) |

`KVar` normalises names: `KVar("my.flag-name")` → `MY_FLAG_NAME`.

### Expressions

```python
kc.KVar("A") & kc.KVar("B")   # A && B
kc.KVar("A") | kc.KVar("B")   # A || B
~kc.KVar("A")                  # !A
kc.any_of(a, b, c)             # a || b || c
kc.all_of(a, b, c)             # a && b && c
```

Simplification rules apply:  `A & ~A` → `n`,  `~(A & B)` → `!A || !B`, etc.

### Options

All option types share the same fluent builder API:

```python
kc.KOptionBool(kc.KVar("NAME"), "Prompt text")
    .add_range(min, max)                       # int/hex only
    .add_default(value)                        # unconditional default
    .add_default(value, when=kc.KVar("COND")) # conditional default
    .add_depends(kc.KVar("DEP"))              # depends on DEP
    .add_selects(kc.KVar("SYM1"), kc.KVar("SYM2"))
    .add_help("First line.", "Second line.")
```

| Class | Type keyword |
|---|---|
| `KOptionBool` | `bool` |
| `KOptionString` | `string` |
| `KOptionInt` | `int` |
| `KOptionHex` | `hex` |
| `KMenuConfig` | `menuconfig` |

### Blocks

```python
kc.KMenu("Title", *items)         # menu "Title" … endmenu
kc.KIf(condition, *items)         # if COND … endif
kc.KChoice("Prompt", *options)    # choice … endchoice
kc.KSource("path/to/Kconfig")     # source "path/to/Kconfig"
kc.KComment("visible comment")    # comment "visible comment"
```

---

## Custom language

To target a different output format, define a new `Language` and subclass the
expression types you need:

```python
from dsl import Language, VarBool, VarName, VarNot, VarAnd, VarOr

cmake = Language("cmake")

class CMakeBool(VarBool[cmake]):
    def __str__(self): return "TRUE" if self.value else "FALSE"

class CMakeName(VarName[cmake]):
    def __str__(self): return self.name

class CMakeNot(VarNot[cmake]):
    def __str__(self): return f"NOT {self.child}"

class CMakeAnd(VarAnd[cmake]):
    def __str__(self): return f"{self.left} AND {self.right}"

class CMakeOr(VarOr[cmake]):
    def __str__(self): return f"{self.left} OR {self.right}"

cmake.validate()   # checks that Bool, Name, Not, And, Or are all registered

a = CMakeName("HAVE_FOO")
b = CMakeName("HAVE_BAR")
print(a & b)   # HAVE_FOO AND HAVE_BAR
print(~(a & b))  # HAVE_FOO AND HAVE_BAR → NOT HAVE_FOO OR NOT HAVE_BAR
```

---

## Examples

Run all examples:

```bash
cd examples
bash run_all.sh          # summary only
bash run_all.sh -v       # full output
```

| File | Covers |
|---|---|
| `01_core_algebra.py` | Custom language, all expression types, simplification rules |
| `02_make.py` | All Make nodes: variables, assignments, rules, conditionals, functions |
| `03_kconfig.py` | All Kconfig nodes: options, menus, choices, conditions |
