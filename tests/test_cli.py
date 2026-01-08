import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from am_core.cli import mermaid, build_graph_from_root
from am_core.feature.feature_unit import FEATURE_UNITS


def test_cli_mermaid_single_root():
    """Test mermaid command with single root."""
    FEATURE_UNITS.clear()

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("""
from am_core.feature.feature_unit import feature_unit

@feature_unit(id="cli_unit")
def cli_func():
    pass
""")

        runner = CliRunner()
        result = runner.invoke(mermaid, ["--root", temp_dir, "--pkg_path", temp_dir, "--output", "output.md"])
        assert result.exit_code == 0
        assert "Mermaid graph saved to output.md" in result.output
        assert Path("output.md").exists()


def test_cli_mermaid_multiple_roots():
    """Test mermaid command with multiple roots."""
    FEATURE_UNITS.clear()

    with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
        # Root 1
        test_file1 = Path(temp_dir1) / "mod1.py"
        test_file1.write_text("""
from am_core.feature.feature_unit import feature_unit

@feature_unit(id="unit1")
def func1():
    pass
""")

        # Root 2
        test_file2 = Path(temp_dir2) / "mod2.py"
        test_file2.write_text("""
from am_core.feature.feature_unit import feature_unit

@feature_unit(id="unit2")
def func2():
    pass
""")

        graph = build_graph_from_root([temp_dir1, temp_dir2])
        ids = {u.id for u in graph.units}
        assert ids == {"unit1", "unit2"}


def test_cli_output_mermaid():
    """Test that mermaid output contains expected content."""
    def func1():
        pass

    def func2():
        pass

    from am_core.feature.feature_unit import FeatureUnit
    units = [
        FeatureUnit(fn=func1, id="out_unit1", depends_on=[func2]),
        FeatureUnit(fn=func2, id="out_unit2")
    ]

    from am_core.graph import FeatureUnitGraph
    graph = FeatureUnitGraph(units)
    output = graph.to_mermaid(for_markdown=False)
    assert "graph TD" in output
    assert "out_unit1" in output
    assert "out_unit2 --> out_unit1" in output