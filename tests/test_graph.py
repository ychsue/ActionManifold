import pytest
from am_core.graph import FeatureUnitGraph
from am_core.feature.feature_unit import FeatureUnit


def test_graph_nodes():
    """Test that graph contains correct nodes."""
    def func1():
        pass

    def func2():
        pass

    units = [
        FeatureUnit(fn=func1, id="unit1"),
        FeatureUnit(fn=func2, id="unit2")
    ]

    graph = FeatureUnitGraph(units)
    assert len(graph.graph.nodes) == 2
    assert "unit1" in graph.graph.nodes
    assert "unit2" in graph.graph.nodes


def test_graph_edges():
    """Test that graph contains correct edges based on dependencies."""
    def func1():
        pass

    def func2():
        pass

    units = [
        FeatureUnit(fn=func1, id="unit1", depends_on=[func2]),
        FeatureUnit(fn=func2, id="unit2")
    ]

    graph = FeatureUnitGraph(units)
    assert ("unit2", "unit1") in graph.graph.edges


def test_graph_dep_lookup():
    """Test dependency lookup in graph."""
    def func1():
        pass

    def func2():
        pass

    units = [
        FeatureUnit(fn=func1, id="unit1", depends_on=[func2]),
        FeatureUnit(fn=func2, id="unit2")
    ]

    graph = FeatureUnitGraph(units)
    # Test shortest path
    path = graph.shortest_path("unit2", "unit1")
    assert path == ["unit2", "unit1"]


def test_graph_unknown_dep():
    """Test handling of unknown dependencies."""
    def func1():
        pass

    def unknown_func():
        pass

    units = [
        FeatureUnit(fn=func1, id="unit1", depends_on=[unknown_func])
    ]

    graph = FeatureUnitGraph(units)
    # Should add external node
    assert len(graph.units) == 2  # Original + external
    external_ids = [u.id for u in graph.units if u.id.startswith("nounit_")]
    assert len(external_ids) == 1