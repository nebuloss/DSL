"""Core node layer: Line, NullNode, ListNode, IndentedNode/FixedNode, stacks."""
import pytest

from dsl.node import Line, NullNode, nullNode
from dsl.content import TextNode
from dsl.container import (
    IndentedNode, FixedNode, NodeStack, NodeBlock, DelimitedNodeBlock,
)


def test_line_indentation():
    assert str(Line(2, "foo")) == "\t\tfoo"
    assert str(Line(0, "x")) == "x"
    assert str(Line(-3, "x")) == "x"          # negative clamps to 0
    assert str(Line(3, "")) == ""             # empty value never indented


def test_nullnode_is_singleton_and_empty():
    assert NullNode() is nullNode
    assert str(nullNode) == ""
    assert list(nullNode.render()) == []


def test_listnode_mutation():
    t = TextNode("a")
    t.append("b").extend(["c", "d"])
    assert list(t) == ["a", "b", "c", "d"]
    assert t[0] == "a"
    assert len(t) == 4


def test_listnode_repeat():
    t = TextNode("a", "b")
    t.repeat(2)
    assert list(t) == ["a", "b", "a", "b"]

def test_listnode_repeat_zero_clears():
    t = TextNode("a", "b")
    t.repeat(0)
    assert list(t) == []

def test_listnode_repeat_requires_int():
    with pytest.raises(TypeError):
        TextNode("a").repeat("2")


def test_indented_node_relative_offset():
    assert str(IndentedNode(TextNode("x"), 2)) == "\t\tx"
    # offset is relative to the level passed in
    assert list(IndentedNode(TextNode("x"), 1).render(1))[0].level == 2


def test_fixed_node_absolute_level():
    n = FixedNode(TextNode("x"), 0)
    # ignores the parent level entirely
    assert list(n.render(5))[0].level == 0


def test_nodestack_margin_between_children():
    from dsl.content import BlankLineNode
    ns = NodeStack(TextNode("a"), TextNode("b"), margin=BlankLineNode())
    assert str(ns) == "a\n\nb"

def test_nodestack_default_no_margin():
    ns = NodeStack(TextNode("a"), TextNode("b"))
    assert str(ns) == "a\nb"


def test_nodeblock_indents_children():
    nb = NodeBlock(TextNode("head"), TextNode("c1"), TextNode("c2"))
    assert str(nb) == "head\n\tc1\n\tc2"


def test_delimited_block_appends_end():
    blk = DelimitedNodeBlock(TextNode("begin"), TextNode("end"), TextNode("body"))
    assert str(blk) == "begin\n\tbody\nend"


def test_find_by_tags():
    inner = TextNode("x").addTags("target")
    nb = NodeBlock(TextNode("head"), inner, TextNode("other"))
    found = list(nb.find("target"))
    assert found == [inner]
    assert list(nb.find("nope")) == []
