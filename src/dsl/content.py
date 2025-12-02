from abc import ABC, abstractmethod
from typing import Iterator, Optional, List

from dsl.container import SimpleNodeStack
from dsl.node import Line, Node

class LinesNode(Node, ABC):
    """
    Base class for content nodes that render in terms of lines.
    Subclasses implement lines() and return raw strings without indentation.
    """

    @abstractmethod
    def lines(self) -> Iterator[str]:
        """
        Raw text lines (without indentation).
        A fresh iterator can be created on each call.
        """

        raise NotImplementedError

    def render(self, level: int = 0) -> Iterator[Line]:
        lvl = max(0, int(level))
        for value in self.lines():
            yield Line(lvl, value)


class BlankLineNode(LinesNode):
    """Vertical space: N empty lines."""

    def __init__(self, lines: int = 1) -> None:
        super().__init__()
        self._count = max(0, int(lines))

    @property
    def count(self) -> int:
        """Number of blank lines."""
        return self._count

    def __len__(self) -> int:
        return self._count

    def lines(self) -> Iterator[str]:
        for _ in range(self._count):
            yield ""


class TextNode(LinesNode):
    """
    Default relative text node.
    Indentation level comes from render(level).
    """

    def __init__(self, *lines: str) -> None:
        super().__init__()
        self._lines: List[str] = list(lines)

    def lines(self) -> Iterator[str]:
        return iter(self._lines)


class FixedTextNode(TextNode):
    """
    Text node with a fixed indentation level given at construction.
    Ignores the level argument of render().
    """

    def __init__(self, *lines: str, level: int = 0) -> None:
        super().__init__(*lines)
        self._fixed_level = max(0, int(level))

    @property
    def fixed_level(self) -> int:
        return self._fixed_level

    def render(self, level: int = 0) -> Iterator[Line]:
        lvl = self._fixed_level
        for value in self.lines():
            yield Line(lvl, value)


class WordsNode(LinesNode, ABC):
    """
    Base class for nodes expressed as words.

    Subclasses implement words(), which returns an iterator of words.
    By default, all words are joined into a single line using sep.
    """

    def __init__(self, sep: str = " ") -> None:
        super().__init__()
        if len(sep)!=1:
            raise ValueError("Expecting one character sep")
        self._sep = sep

    @property
    def sep(self) -> str:
        return self._sep

    @abstractmethod
    def words(self) -> Iterator[str]:
        """
        Raw words for this node.
        """

        raise NotImplementedError

    def lines(self) -> Iterator[str]:
        # Default behavior: one line built from all words.
        yield self._sep.join(self.words())

class WordlistNode(WordsNode):
    """
    Basic concrete WordsNode backed by a list of words.

      WordListNode("foo", "bar") -> "foo bar"

    You can tweak the separator with sep="," etc.
    """

    def __init__(self, *words: str, sep: str = " ") -> None:
        super().__init__(sep=sep)
        self._words: List[str] = list(words)


    def words(self) -> Iterator[str]:
        return iter(self._words)

class WordAlignedStack[TChild:WordsNode](LinesNode, SimpleNodeStack[TChild]):
    """
    Align WordsNode children on word boundaries.

    - Each child provides its words via child.words()
    - Each child has a separator via child.sep (single character)
    - For alignment we treat each aligned word as a "cell" of `word + sep`,
      except the suffix part, which is left untouched.

    All word columns across all rows participate in alignment:
    for each row, all words except the last one form the aligned cells,
    and the last word (if present) is part of the suffix.
    """

    def __init__(self, *children: TChild):
        SimpleNodeStack.__init__(self, *children)

    # ---- helpers ----

    @staticmethod
    def _cell_lengths(cells: List[str]) -> List[int]:
        """Return a list of lengths for the given cell strings."""
        return [len(c) for c in cells]

    @staticmethod
    def _compare_lengths(max_lengths: List[int], current: List[int]) -> None:
        """
        Update max_lengths in place so it becomes the element-wise max
        between itself and current. Extends max_lengths if needed.
        """
        for i, length in enumerate(current):
            if i == len(max_lengths):
                max_lengths.append(length)
            elif length > max_lengths[i]:
                max_lengths[i] = length

    @staticmethod
    def _pad_cell(cell: str, length: int, sep: str) -> str:
        """
        Return cell padded or truncated to exactly `length` characters.

        Padding is done by repeating `sep` and truncating:
          (cell + sep * length)[:length]
        """
        if len(cell) >= length:
            return cell[:length]
        base = cell + (sep * length)
        return base[:length]

    @classmethod
    def _pad_cells(
        cls,
        cells: List[str],
        lengths: List[int],
        sep: str,
    ) -> List[str]:
        """
        Apply predefined column lengths to a list of cells.

        Let:
          align_cols = min(len(lengths), len(cells))

        Only columns 0..align_cols-1 are padded. Extra cells (if any)
        are left untouched.
        """
        if not cells:
            return []

        align_cols = min(len(lengths), len(cells))
        if align_cols <= 0:
            return list(cells)

        result: List[str] = []
        for i, c in enumerate(cells):
            if i < align_cols:
                result.append(cls._pad_cell(c, lengths[i], sep))
            else:
                result.append(c)
        return result

    # ---- LinesNode API ----

    def lines(self) -> Iterator[str]:
        children: List[TChild] = list(self)
        if not children:
            return

        # Extract words and separators from children
        rows: List[List[str]] = [list(c.words()) for c in children]
        seps: List[str] = [c.sep for c in children]

        if not any(rows):
            return

        max_cols = max(len(words) for words in rows)
        if max_cols <= 1:
            # 0 or 1 word per line: nothing to align, delegate
            for child in children:
                yield from child.lines()
            return

        # Pass 1: build cells/suffixes and compute max lengths
        max_lengths: List[int] = []
        all_cells: List[List[str]] = []
        all_suffixes: List[str] = []

        for words, sep in zip(rows, seps):
            n = len(words)
            aligned_cells = max(0, n - 1)

            # cells: word + sep for aligned part
            cells = [w + sep for w in words[:aligned_cells]]

            # suffix: everything from aligned_cells onward (usually last word)
            suffix_words = words[aligned_cells:]
            suffix = sep.join(suffix_words) if suffix_words else ""

            all_cells.append(cells)
            all_suffixes.append(suffix)

            current_lengths = self._cell_lengths(cells)
            self._compare_lengths(max_lengths, current_lengths)

        # Pass 2: pad cells and produce final lines
        for cells, suffix, sep in zip(all_cells, all_suffixes, seps):
            if not cells:
                yield suffix
            else:
                padded = self._pad_cells(cells, max_lengths, sep)
                yield "".join(padded) + suffix
