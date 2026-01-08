import pytest
from datetime import datetime
from am_core.feature.feature_unit import FeatureUnit, feature_unit, FEATURE_UNITS, get_fn_key


def test_feature_unit_registration():
    """Test that @feature_unit registers a FeatureUnit correctly."""
    # Clear registry for test
    FEATURE_UNITS.clear()

    @feature_unit(id="test_unit", display_name="Test Unit")
    def test_function():
        pass

    key = get_fn_key(test_function)
    assert key in FEATURE_UNITS
    unit = FEATURE_UNITS[key]
    assert unit.id == "test_unit"
    assert unit.display_name == "Test Unit"
    assert unit.status == "pending"


def test_feature_unit_metadata():
    """Test that metadata is stored correctly."""
    FEATURE_UNITS.clear()

    due_date = datetime(2026, 12, 31)
    @feature_unit(
        id="meta_test",
        display_name="Metadata Test",
        status="planned",
        belongs_to=["TestGroup"],
        due=due_date,
        priority=5,
        notes="Test notes"
    )
    def meta_function():
        pass

    key = get_fn_key(meta_function)
    unit = FEATURE_UNITS[key]
    assert unit.status == "planned"
    assert unit.belongs_to == ["TestGroup"]
    assert unit.due == due_date
    assert unit.priority == 5
    assert unit.notes == "Test notes"


def test_feature_unit_depends():
    """Test that depends_on is set correctly."""
    FEATURE_UNITS.clear()

    def dep_function():
        pass

    @feature_unit(id="dependent", depends=[dep_function])
    def dependent_function():
        pass

    key = get_fn_key(dependent_function)
    unit = FEATURE_UNITS[key]
    assert len(unit.depends_on) == 1
    assert unit.depends_on[0] == dep_function


def test_unit_no_duplicate_registration():
    """Test that the same function is not registered twice."""
    FEATURE_UNITS.clear()

    @feature_unit(id="unique_unit")
    def unique_function():
        pass

    # Apply decorator again
    decorated = feature_unit(id="unique_unit")(unique_function)

    key = get_fn_key(unique_function)
    assert len(FEATURE_UNITS) == 1  # Should still be one
    assert FEATURE_UNITS[key].id == "unique_unit"