import pytest
import tempfile
import os
from pathlib import Path
from am_core.feature.collector import collect_feature_units
from am_core.feature.feature_unit import FEATURE_UNITS, feature_unit


def test_collect_single_root():
    """Test collecting feature units from a single root directory."""
    FEATURE_UNITS.clear()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test Python file with a feature unit
        test_file = Path(temp_dir) / "test_module.py"
        test_file.write_text("""
from am_core.feature.feature_unit import feature_unit

@feature_unit(id="test_collect_unit")
def test_function():
    pass
""")

        units = collect_feature_units(temp_dir)
        assert len(units) == 1
        assert units[0].id == "test_collect_unit"


def test_collect_multiple_roots():
    """Test collecting from multiple root directories."""
    FEATURE_UNITS.clear()

    with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
        # First root
        test_file1 = Path(temp_dir1) / "module1.py"
        test_file1.write_text("""
from am_core.feature.feature_unit import feature_unit

@feature_unit(id="unit1")
def func1():
    pass
""")

        # Second root
        test_file2 = Path(temp_dir2) / "module2.py"
        test_file2.write_text("""
from am_core.feature.feature_unit import feature_unit

@feature_unit(id="unit2")
def func2():
    pass
""")

        units = collect_feature_units(temp_dir1)
        units.extend(collect_feature_units(temp_dir2))
        ids = {u.id for u in units}
        assert ids == {"unit1", "unit2"}


def test_collect_no_duplicate_import():
    """Test that the same module is not imported multiple times."""
    FEATURE_UNITS.clear()

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "duplicate.py"
        test_file.write_text("""
from am_core.feature.feature_unit import feature_unit

@feature_unit(id="dup_unit")
def dup_func():
    pass
""")

        # Collect twice
        units1 = collect_feature_units(temp_dir)
        units2 = collect_feature_units(temp_dir)
        # Should not duplicate
        assert len(FEATURE_UNITS) == 1


def test_collect_invalid_root():
    """Test that invalid root path raises ValueError."""
    with pytest.raises(ValueError, match="Root path does not exist"):
        collect_feature_units("/nonexistent/path")