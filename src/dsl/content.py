"""
Content nodes — leaves of the render tree.

These nodes hold actual text; they sit at the bottom of the node hierarchy
and do not contain child Nodes (unlike container.py which wraps other Nodes).

LinesNode / WordsNode
─────────────────────
Two rendering strategies:
  • LinesNode  — each item becomes one indented line.
  • WordsNode  — all words are joined on a single line with a separator.

WordAlignedStack
────────────────
Aligns a column of WordsNode children so that corresponding words line up.

Algorithm (two passes):
  Pass 1 — for each child, split words into "cells" and "suffix":
             cells  = words[0 .. n-2],  each padded with sep to form a cell
             suffix = words[n-1]         (the last word, never padded)
           Track the maximum cell width per column across all children.
  Pass 2 — pad every cell to the column maximum, then concatenate.

Example (MAssignmentList):
    ["CC",  "=",  "gcc"]     →  cells=["CC "," = "], suffix="gcc"
    ["LONGER", ":=", "val"]  →  cells=["LONGER "," := "], suffix="val"
    After alignment:
    "CC      =  gcc"
    "LONGER  := val"
"""
from typing import Iterator, List

from dsl.node import IterableNode, Line, ListNode, SupportsStr

class LinesNode(IterableNode[SupportsStr]):
    """Each item returned by __iter__ becomes one indented line."""

    def render(self, level: int = 0) -> Iterator[Line]:
        lvl = max(0, int(level))
        for value in self:
            yield Line(lvl, str(value))

class WordsNode(IterableNode[SupportsStr]):
    """All words from __iter__ are joined into a single line using sep."""

    def __init__(self, sep: str = " ") -> None:
        super().__init__()
        self._sep = sep

    @property
    def sep(self) -> str:
        return self._sep

    def render(self, level: int = 0) -> Iterator[Line]:
        yield Line(level, self._sep.join(str(word) for word in self))

class BlankLineNode(LinesNode):
    """Vertical space: N empty lines."""

    def __init__(self, lines: int = 1) -> None:
        super().__init__()
        self._count = max(0, int(lines))

    @property
    def count(self) -> int:
        return self._count

    def __iter__(self) -> Iterator[str]:
        for _ in range(self._count):
            yield ""

class TextNode(ListNode[SupportsStr], LinesNode):
    """A list of strings, each rendered as one indented line."""
    pass

class WordlistNode(ListNode[SupportsStr], WordsNode):
    """A list of words joined into a single line.

    WordlistNode("foo", "bar")  →  "foo bar"
    """
    pass


# ── Column-aligned word containers ───────────────────────────────────────────

class WordAlignedContainer[TChild: WordsNode](LinesNode):
    """Aligns WordsNode children on word-column boundaries (see module doc)."""

    # ── Pass-1 helpers ────────────────────────────────────────────────────

    @staticmethod
    def _cell_lengths(cells: List[str]) -> List[int]:
        return [len(c) for c in cells]

    @staticmethod
    def _compare_lengths(max_lengths: List[int], current: List[int]) -> None:
        """Extend and update max_lengths to the element-wise maximum."""
        for i, length in enumerate(current):
            if i == len(max_lengths):
                max_lengths.append(length)
            elif length > max_lengths[i]:
                max_lengths[i] = length

    @staticmethod
    def _pad_cell(cell: str, length: int, sep: str) -> str:
        """Right-pad *cell* to exactly *length* chars using *sep* as fill."""
        if len(cell) >= length:
            return cell[:length]
        return (cell + sep * length)[:length]

    @classmethod
    def _pad_cells(cls, cells: List[str], lengths: List[int], sep: str) -> List[str]:
        """Apply per-column widths; extra cells beyond lengths are left alone."""
        if not cells:
            return []
        align_cols = min(len(lengths), len(cells))
        result: List[str] = []
        for i, c in enumerate(cells):
            result.append(cls._pad_cell(c, lengths[i], sep) if i < align_cols else c)
        return result

    # ── LinesNode API ────────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[str]:
        children: List[TChild] = list(super().__iter__())
        if not children:
            return

        rows: List[List[str]] = [list(str(w) for w in c) for c in children]
        seps: List[str]       = [c.sep for c in children]

        if not any(rows):
            return

        max_cols = max(len(r) for r in rows)
        if max_cols <= 1:
            # Nothing to align when every row has at most one word.
            for child in children:
                yield str(child)
            return

        # Pass 1 — build cells/suffixes and compute per-column max widths.
        max_lengths: List[int]         = []
        all_cells:   List[List[str]]   = []
        all_suffixes: List[str]        = []

        for words, sep in zip(rows, seps):
            n = len(words)
            aligned_cols = max(0, n - 1)
            # Each aligned cell = word + sep  (the separator is part of the
            # cell so padding naturally leaves a gap before the next column).
            cells  = [w + sep for w in words[:aligned_cols]]
            suffix = sep.join(words[aligned_cols:]) if words[aligned_cols:] else ""
            all_cells.append(cells)
            all_suffixes.append(suffix)
            self._compare_lengths(max_lengths, self._cell_lengths(cells))

        # Pass 2 — pad to column widths and emit final lines.
        for cells, suffix, sep in zip(all_cells, all_suffixes, seps):
            if not cells:
                yield suffix
            else:
                padded = self._pad_cells(cells, max_lengths, sep)
                yield "".join(padded) + suffix


class WordAlignedStack[TChild: WordsNode](WordAlignedContainer[TChild], ListNode[TChild]):
    """Concrete aligned stack backed by a list (the common case)."""
    pass
