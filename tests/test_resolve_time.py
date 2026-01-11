import pytest
from datetime import datetime, timedelta
from am_core.feature.resolve_time import resolve_time, resolve_duration, resolve_unit_times
from am_core.graph import FeatureUnitGraph
from am_core.feature.feature_unit import FeatureUnit


def test_resolve_time_absolute():
    """Test resolving absolute datetime."""
    dt = datetime(2026, 1, 10)
    graph = FeatureUnitGraph([])  # Empty graph for absolute time
    assert resolve_time(dt, graph) == dt


def test_resolve_time_relative_by_function():
    """Test resolving relative time using function reference."""
    def ref_func():
        pass

    ref_unit = FeatureUnit(
        fn=ref_func,
        id="ref_unit",
        scheduled=datetime(2026, 1, 1),
        due=datetime(2026, 1, 5)
    )
    graph = FeatureUnitGraph([ref_unit])

    expr = (ref_func, "scheduled", 3)
    result = resolve_time(expr, graph)
    expected = datetime(2026, 1, 1) + timedelta(days=3)
    assert result == expected


def test_resolve_time_relative_by_id():
    """Test resolving relative time using unit ID."""
    def ref_func():
        pass

    ref_unit = FeatureUnit(
        fn=ref_func,
        id="ref_unit",
        scheduled=datetime(2026, 1, 1)
    )
    graph = FeatureUnitGraph([ref_unit])

    expr = ("ref_unit", "scheduled", 5)
    result = resolve_time(expr, graph)
    expected = datetime(2026, 1, 1) + timedelta(days=5)
    assert result == expected


def test_resolve_time_function_not_found():
    """Test error when referenced function not in graph."""
    def missing_func():
        pass

    graph = FeatureUnitGraph([])
    expr = (missing_func, "scheduled", 1)
    with pytest.raises(ValueError, match="Function .* not found in graph"):
        resolve_time(expr, graph)


def test_resolve_duration_absolute():
    """Test resolving absolute duration."""
    dur = timedelta(days=7)
    graph = FeatureUnitGraph([])
    assert resolve_duration(dur, graph) == dur


def test_resolve_duration_relative():
    """Test resolving relative duration."""
    def ref_func():
        pass

    ref_unit = FeatureUnit(
        fn=ref_func,
        id="ref_unit",
        duration=timedelta(days=10)
    )
    graph = FeatureUnitGraph([ref_unit])

    expr = (ref_func, "duration", 2)
    result = resolve_duration(expr, graph)
    expected = timedelta(days=12)
    assert result == expected


def test_resolve_unit_times_scheduled_and_duration():
    """Test rule 1: scheduled + duration -> due."""
    def unit_func():
        pass

    unit = FeatureUnit(
        fn=unit_func,
        id="test_unit",
        scheduled=datetime(2026, 1, 1),
        duration=timedelta(days=5)
    )
    graph = FeatureUnitGraph([unit])

    result = resolve_unit_times(unit, graph)
    assert result.start == datetime(2026, 1, 1)
    assert result.end == datetime(2026, 1, 6)


def test_resolve_unit_times_scheduled_and_due():
    """Test rule 2: scheduled + due -> duration."""
    def unit_func():
        pass

    unit = FeatureUnit(
        fn=unit_func,
        id="test_unit",
        scheduled=datetime(2026, 1, 1),
        due=datetime(2026, 1, 10)
    )
    graph = FeatureUnitGraph([unit])

    result = resolve_unit_times(unit, graph)
    assert result.start == datetime(2026, 1, 1)
    assert result.end == datetime(2026, 1, 10)
    # duration should be calculated
    assert result.duration == timedelta(days=9)


def test_resolve_unit_times_duration_with_depends():
    """Test rule 3: duration + depends -> scheduled = max(depends.end)."""
    def dep_func():
        pass

    def unit_func():
        pass

    dep_unit = FeatureUnit(
        fn=dep_func,
        id="dep_unit",
        scheduled=datetime(2026, 1, 1),
        due=datetime(2026, 1, 5)
    )
    unit = FeatureUnit(
        fn=unit_func,
        id="test_unit",
        duration=timedelta(days=3),
        depends_on=[dep_func]
    )
    graph = FeatureUnitGraph([dep_unit, unit])

    result = resolve_unit_times(unit, graph)
    assert result.start == datetime(2026, 1, 5)  # max of dep.end
    assert result.end == datetime(2026, 1, 8)


def test_resolve_unit_times_due_and_duration():
    """Test rule 4: due + duration -> scheduled."""
    def unit_func():
        pass

    unit = FeatureUnit(
        fn=unit_func,
        id="test_unit",
        due=datetime(2026, 1, 10),
        duration=timedelta(days=5)
    )
    graph = FeatureUnitGraph([unit])

    result = resolve_unit_times(unit, graph)
    assert result.start == datetime(2026, 1, 5)
    assert result.end == datetime(2026, 1, 10)


def test_resolve_unit_times_no_times():
    """Test unit with no time information."""
    def unit_func():
        pass

    unit = FeatureUnit(
        fn=unit_func,
        id="test_unit"
    )
    graph = FeatureUnitGraph([unit])

    result = resolve_unit_times(unit, graph)
    assert result.start is None
    assert result.end is None