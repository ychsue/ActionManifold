"""
AM-Core Development Semantics CLI
=================================

Usage examples:

1. Generate roadmap.md for entire project:
   python -m am_core.cli roadmap --root am_project

2. Visualize dependency graph:
   python -m am_core.cli graph --root am_project

3. Visualize pending-only dependency graph:
   python -m am_core.cli graph --root am_project --pending

4. Visualize timeline (scheduled → due):
   python -m am_core.cli timeline --root am_project

5. Visualize Gantt chart:
   python -m am_core.cli gantt --root am_project

This CLI automatically:
- Recursively scans the project directory
- Collects all FeatureUnits (methods with @unit)
- Builds a FeatureUnitGraph
- Generates reports and visualizations
"""

from typing import List, Optional
import click
from ..feature.collector import collect_feature_units
from ..feature.feature_unit import feature_unit
from ..graph import FeatureUnitGraph
from ..feature.report import generate_roadmap
from ..feature.visualize import visualize_timeline, visualize_gantt

@click.group()
def cli():
    """ActionManifold Development Semantics CLI"""
    pass

# ------------------------------------------------------------
# Helper: Build graph from root directory
# ------------------------------------------------------------
def build_graph_from_root(root_paths: list[str], pkg_path: Optional[str] = None) -> FeatureUnitGraph:
    units = []
    for root_path in root_paths:
        units.extend(collect_feature_units(root_path, pkg_path=pkg_path))
    return FeatureUnitGraph(units)

def find_kickoff_node_id(graph: FeatureUnitGraph, start_suffix: str) -> str:
    matched_ids = [uid for uid in graph.units_by_id.keys() if uid.endswith(start_suffix)]
    if not matched_ids:
        raise ValueError(f"No kickoff node ID ends with '{start_suffix}'")
    if len(matched_ids) > 1:
        raise ValueError(f"Multiple kickoff node IDs end with '{start_suffix}': {matched_ids}")
    return matched_ids[0]

# ------------------------------------------------------------
# roadmap
# ------------------------------------------------------------
def cmd_roadmap(root, pkg_path, output, kickoff):
    """Generate roadmap.md"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    try:
        kickoff_id = find_kickoff_node_id(graph, kickoff or "kickoff")
        generate_roadmap(graph, output, kickoff=kickoff_id)
        click.echo(f"✅ Roadmap generated at {output}")
    except ValueError as e:
        click.echo(f"❌ roadmap Error: {e}")

@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--output", default="docs/roadmap.md")
@click.option("--kickoff", default=None)
def roadmap(root, pkg_path, output, kickoff):
    """Generate roadmap.md"""
    cmd_roadmap(root, pkg_path, output, kickoff)


# ------------------------------------------------------------
# dependency graph
# ------------------------------------------------------------
def cmd_dependency(root, pkg_path, pending, output):
    """Visualize dependency graph"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    if output:
        content = graph.to_mermaid()
        if output == "str":
            click.echo(content)
            return content
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
            click.echo(f"✅ Graph saved to {output}")
    else:
        graph.visualize(pending=pending)

@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--pending", is_flag=True)
@click.option("--output", default="docs/graph.md", help="If specified and not 'str', save markdown to this file. If it is 'str', print to console")
def dependency(root, pkg_path, pending, output):
    """Visualize dependency graph"""
    return cmd_dependency(root, pkg_path, pending, output)
# ------------------------------------------------------------
# timeline
# ------------------------------------------------------------
def cmd_timeline(root, pkg_path, pending, output):
    """Visualize timeline"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    if output:
        # 將 timeline 輸出到 .md
        content = "# Timeline\n\n"
        content += graph.to_mermaid_timeline(pending=pending)
        if output == "str":
            click.echo(content)
            return content
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"✅ Timeline saved to {output}")
    else:
        visualize_timeline(graph, pending=pending)

@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--pending", is_flag=True)
@click.option("--output", default="docs/timeline.md", help="If specified and not 'str', save markdown to this file. If it is 'str', print to console")
def timeline(root, pkg_path, pending, output):
    """Visualize timeline"""
    return cmd_timeline(root, pkg_path, pending, output)

# ------------------------------------------------------------
# gantt
# ------------------------------------------------------------

def cmd_gantt(root, pkg_path, pending, output):
    """Visualize Gantt chart"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    if output:
        content = graph.to_mermaid_gantt(pending=pending)
        if output == "str":
            click.echo(content)
            return content
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"✅ Gantt chart saved to {output}")
    else:
        visualize_gantt(graph, pending=pending)

@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--pending", is_flag=True)
@click.option("--output", default="docs/gantt.md", help="If specified and not 'str', save markdown to this file. If it is 'str', print to console")
def gantt(root, pkg_path, pending, output):
    """Visualize Gantt chart"""
    return cmd_gantt(root, pkg_path, pending, output)

# ------------------------------------------------------------
# mainline
# ------------------------------------------------------------
def cmd_mainline(root, pkg_path, start, output):
    """Analyze mainline from a kickoff node"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    # 找出真正的 kickoff node ID
    try:
        kickoff_id = find_kickoff_node_id(graph, start)
    except ValueError as e:
        click.echo(f"❌ mainline Error: {e}")
        return

    directed = graph.directed_mainline(kickoff_id)
    weak = graph.weakly_connected_mainline(kickoff_id)
    completion = graph.mainline_completion(kickoff_id)
    critical = graph.directed_pending_critical_path(kickoff_id)
    external = graph.external_dependencies(kickoff_id)

    content: str = f"# Mainline Analysis from {start}\n\n"
    def add_content_line(origin_line:str, line: str):
        if output:
            origin_line += line + "\n"
        else:
            click.echo(line)
        return origin_line

    content = add_content_line(content, f"# Directed mainline (internal only) from {start}")
    for u in directed:
        content = add_content_line(content, f"  - {u} [{graph.units_by_id[u].status}]")

    content = add_content_line(content, f"\n# Completion (internal mainline): {completion*100:.1f}%")

    content = add_content_line(content, f"\n# Directed pending critical path (internal):")
    if critical:
        for u in critical:
            content = add_content_line(content, f"  -> {u} [{graph.units_by_id[u].status}]")
    else:
        content = add_content_line(content, "  (no pending critical path)")

    content = add_content_line(content, f"\n# Weakly connected mainline (internal + external) from {start}:")
    for u in weak:
        tag = "internal" if graph.is_internal(u) else "external"
        status = graph.units_by_id[u].status if graph.is_internal(u) else "unknown"
        content = add_content_line(content, f"  - {u} [{tag}] [{status}]")
    content = add_content_line(content, f"\n# External dependencies in this component:")
    if external:
        for u in external:
            content = add_content_line(content, f"  - {u}")
    else:
        content = add_content_line(content, "  (none)")
        
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"✅ Mainline analysis saved to {output}")


@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--start", required=True, help="Kickoff node ID ending with this string")
@click.option("--output", default="docs/mainline.md", help="If specified, save visualization to this file")
def mainline(root, pkg_path, start, output):
    """Analyze mainline from a kickoff node"""
    return cmd_mainline(root, pkg_path, start, output)


@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--start", default="kickoff", help="Kickoff node ID ending with this string")
def dump_all_dev_mds(root: List[str], pkg_path: Optional[str], start: Optional[str]):
    """Dump all docs/dev_*.md files for the project"""
    
    # Build Roadmap
    cmd_roadmap(root, pkg_path, output="docs/dev_roadmap.md", kickoff=start)
    
    # Build Dependency Graph
    content = "# Dependency Graph\n\n"
    content += cmd_dependency(root, pkg_path, pending=False, output="str") or ""
    with open("docs/dev_dependency_graph.md", "w", encoding="utf-8") as f:
        f.write(content)
    
    # Build Timeline
    content = "# Timeline\n\n"
    content += cmd_timeline(root, pkg_path, pending=False, output="str") or ""
    content += "\n\n# Timeline (Pending Only)\n\n"
    content += cmd_timeline(root, pkg_path, pending=True, output="str") or ""
    with open("docs/dev_timeline.md", "w", encoding="utf-8") as f:
        f.write(content)
        
    # Build Gantt Chart
    content = "# Gantt Chart\n\n"
    content += cmd_gantt(root, pkg_path, pending=False, output="str") or ""
    content += "\n\n# Gantt Chart (Pending Only)\n\n"
    content += cmd_gantt(root, pkg_path, pending=True, output="str") or ""
    with open("docs/dev_gantt_chart.md", "w", encoding="utf-8") as f:
        f.write(content)
        
    # Build Mainline Analysis
    mainline_output = "docs/dev_mainline_analysis.md"
    cmd_mainline(root, pkg_path, start=start, output=mainline_output)
    
    click.echo("✅ All dev_*.md files have been generated in the docs/ directory.")
# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------
@feature_unit(
    belongs_to=["DevEngine"],
    status="done",
    display_name="AM CLI Entry Point",
    depends=[collect_feature_units, FeatureUnitGraph,
             generate_roadmap, visualize_timeline, visualize_gantt],
    notes="提供 am CLI 入口，串接 roadmap / graph / timeline / gantt / mainline"
)
def main():
    cli()


if __name__ == "__main__":
    main()