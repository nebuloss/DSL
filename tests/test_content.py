"""Content/leaf nodes: lines, words, blank lines, and column alignment."""
from dsl.content import (
    TextNode, WordlistNode, BlankLineNode, WordAlignedStack,
)


def test_textnode_one_line_per_item():
    assert str(TextNode("a", "b", "c")) == "a\nb\nc"

def test_wordlistnode_joins_with_sep():
    assert str(WordlistNode("a", "b", "c")) == "a b c"

def test_wordlistnode_custom_sep():
    wl = WordlistNode("a", "b")
    wl._sep = ","   # sep is set via WordsNode.__init__; verify join uses it
    assert str(wl) == "a,b"


def test_blank_line_node_counts():
    assert str(BlankLineNode(1)) == ""
    assert str(BlankLineNode(2)) == "\n"
    assert str(BlankLineNode(3)) == "\n\n"
    assert str(BlankLineNode(0)) == ""


def test_word_aligned_stack_columns():
    stack = WordAlignedStack(
        WordlistNode("CC", "=", "gcc"),
        WordlistNode("LONGER", ":=", "val"),
    )
    assert str(stack) == "CC     =  gcc\nLONGER := val"


def test_word_aligned_stack_never_truncates_wide_cell():
    # A cell wider than others must not be cut off (regression for _pad_cell).
    stack = WordAlignedStack(
        WordlistNode("X", "=", "1"),
        WordlistNode("VERYLONGNAME", "=", "2"),
    )
    lines = str(stack).split("\n")
    assert lines[1].startswith("VERYLONGNAME =")
    assert lines[0].startswith("X")
    # both '=' columns align
    assert lines[0].index("=") == lines[1].index("=")


def test_word_aligned_single_word_rows_passthrough():
    stack = WordAlignedStack(WordlistNode("only"), WordlistNode("one"))
    assert str(stack) == "only\none"


def test_word_aligned_empty():
    assert str(WordAlignedStack()) == ""
