import pytest
from am_core.graph import FeatureUnitGraph
from am_core.feature.feature_unit import FeatureUnit


def test_mermaid_node_format():
    """Test that Mermaid output formats nodes correctly."""
    def func1():
        pass

    units = [
        FeatureUnit(fn=func1, id="test.unit", display_name="Test Unit", status="done")
    ]

    graph = FeatureUnitGraph(units)
    mermaid = graph.to_mermaid(for_markdown=False)
    assert 'test_unit["Test Unit"]' in mermaid
    assert 'style test_unit fill:green' in mermaid


def test_mermaid_edge_format():
    """Test that Mermaid output formats edges correctly."""
    def func1():
        pass

    def func2():
        pass

    units = [
        FeatureUnit(fn=func1, id="unit1", depends_on=[func2]),
        FeatureUnit(fn=func2, id="unit2")
    ]

    graph = FeatureUnitGraph(units)
    mermaid = graph.to_mermaid(for_markdown=False)
    assert "unit2 --> unit1" in mermaid


def test_mermaid_display_name_fallback():
    """Test that display_name falls back to effective_name."""
    def func1():
        pass

    units = [
        FeatureUnit(fn=func1, id="fallback.unit")  # No display_name
    ]

    graph = FeatureUnitGraph(units)
    mermaid = graph.to_mermaid(for_markdown=False)
    # effective_name should be module.qualname, which includes func1
    assert 'func1' in mermaid