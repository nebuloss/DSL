# Changelog

## 3.0 — 2026-06-08

### Added
- **Type coercion** on constructors: plain `str`/`int`/`bool` are coerced to the
  right node type via a small OO protocol (`VarName.coerce` for names,
  `VarConst.coerce` for literals). Works for Make assignments/rules/conditionals
  and Kconfig option names, defaults, depends, selects, ranges and conditions.
  Fully backward-compatible — existing nodes pass through unchanged.
- **Test suite** (`tests/`, run with `pytest`): expression algebra and
  simplification, node/render layer, language binding, coercion, and the Make
  and Kconfig sublanguages. Added `[project.optional-dependencies] test`.
- `MDefine` is now exported from `dsl.make`.
- `VarExpr` is now hashable (`__hash__` consistent with `__eq__`), so
  expressions can be used in sets/dicts.
- Documentation: accurate quick-starts, a "Concise construction" section, a
  command-quoting note, and a "Testing" section.

### Fixed
- **Make conditional/define blocks no longer emit stray blank lines** between
  the header, body and footer (`ifdef … endif`, `define … endef`,
  `MConditionList` chains). Spacing between blocks is still handled by the
  enclosing `Makefile` margin.
- **`MDefine` emitted `define $(FOO)`** instead of make's required bare name
  `define FOO`.
- **`KVar` name validation**: empty/whitespace names raised `IndexError`; a
  leading-whitespace name such as `" 7"` bypassed the digit check and produced
  an invalid Kconfig symbol. Names are now stripped and validated on the
  normalised form.
- `WordAlignedStack` no longer truncates a cell wider than its column.
- Removed dead/duplicate imports; `pyproject.toml` `requires-python` corrected
  to `>=3.12` (the code uses PEP 695 generics).

### Performance
- `key()` (used by `__eq__`, `__hash__` and every `simplify()` pass) is cached
  per expression, making repeated lookups on a tree O(1) after the first.

### Internal
- `MFunc.args` is now a method (`args()`), consistent with `VarExpr`'s
  structural API, rather than a property.
