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

from typing import Optional
import click
from .feature.collector import collect_feature_units
from .feature.feature_unit import feature_unit
from .graph import FeatureUnitGraph
from .feature.report import generate_roadmap
from .feature.visualize import visualize_timeline, visualize_gantt

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


# ------------------------------------------------------------
# Commands
# ------------------------------------------------------------
def cmd_roadmap(args):
    graph = build_graph_from_root(args.root)
    generate_roadmap(graph, args.output, kickoff=args.kickoff)
    print(f"✅ Roadmap generated at {args.output}")


def cmd_graph(args):
    graph = build_graph_from_root(args.root)
    graph.visualize(pending=args.pending)


def cmd_timeline(args):
    graph = build_graph_from_root(args.root)
    visualize_timeline(graph, pending=args.pending)


def cmd_gantt(args):
    graph = build_graph_from_root(args.root)
    visualize_gantt(graph, pending=args.pending)

def cmd_mainline(args):
    graph = build_graph_from_root(args.root)
    start = args.start

    directed = graph.directed_mainline(start)
    weak = graph.weakly_connected_mainline(start)
    completion = graph.mainline_completion(start)
    critical = graph.directed_pending_critical_path(start)
    external = graph.external_dependencies(start)

    print(f"# Directed mainline (internal only) from {start}")
    for u in directed:
        print(f"  - {u} [{graph.units_by_id[u].status}]")

    print(f"\nCompletion (internal mainline): {completion*100:.1f}%")

    print(f"\nDirected pending critical path (internal):")
    if critical:
        for u in critical:
            print(f"  -> {u} [{graph.units_by_id[u].status}]")
    else:
        print("  (no pending critical path)")

    print(f"\nWeakly connected mainline (internal + external) from {start}:")
    for u in weak:
        tag = "internal" if graph.is_internal(u) else "external"
        status = graph.units_by_id[u].status if graph.is_internal(u) else "unknown"
        print(f"  - {u} [{tag}] [{status}]")

    print(f"\nExternal dependencies in this component:")
    if external:
        for u in external:
            print(f"  - {u}")
    else:
        print("  (none)")


# ------------------------------------------------------------
# mermaid output
# ------------------------------------------------------------
@cli.command()
@click.option("--root", multiple=True, required=True, help="Root paths to scan")
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--output", default="mermaid.md")
def mermaid(root, pkg_path, output):
    """Generate Mermaid dependency graph"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    if output:
        with open(output, "w") as f:
            f.write(graph.to_mermaid())
        click.echo(f"✅ Mermaid graph saved to {output}")
    else:
        print(graph.to_mermaid())


# ------------------------------------------------------------
# roadmap
# ------------------------------------------------------------
@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--output", default="roadmap.md")
@click.option("--kickoff", default=None)
def roadmap(root, pkg_path, output, kickoff):
    """Generate roadmap.md"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    generate_roadmap(graph, output, kickoff=kickoff)
    click.echo(f"✅ Roadmap generated at {output}")


# ------------------------------------------------------------
# graph
# ------------------------------------------------------------
@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--pending", is_flag=True)
def graph(root, pkg_path, pending):
    """Visualize dependency graph"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    graph.visualize(pending=pending)


# ------------------------------------------------------------
# timeline
# ------------------------------------------------------------
@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--pending", is_flag=True)
def timeline(root, pkg_path, pending):
    """Visualize timeline"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    visualize_timeline(graph, pending=pending)


# ------------------------------------------------------------
# gantt
# ------------------------------------------------------------
@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--pending", is_flag=True)
def gantt(root, pkg_path, pending):
    """Visualize Gantt chart"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    visualize_gantt(graph, pending=pending)


# ------------------------------------------------------------
# mainline
# ------------------------------------------------------------
@cli.command()
@click.option("--root", multiple=True, required=True)
@click.option("--pkg_path", default=None, help="Package root path for module naming")
@click.option("--start", required=True, help="Kickoff node ID ending with this string")
def mainline(root, pkg_path, start):
    """Analyze mainline from a kickoff node"""
    graph = build_graph_from_root(root, pkg_path=pkg_path)
    # 找出真正的 kickoff node ID
    matched_ids = [uid for uid in graph.units_by_id.keys() if uid.endswith(start)]
    if not matched_ids:
        raise ValueError(f"No kickoff node ID ends with '{start}'")
    if len(matched_ids) > 1:
        raise ValueError(f"Multiple kickoff node IDs end with '{start}': {matched_ids}")
    kickoff_id = matched_ids[0]

    directed = graph.directed_mainline(kickoff_id)
    weak = graph.weakly_connected_mainline(kickoff_id)
    completion = graph.mainline_completion(kickoff_id)
    critical = graph.directed_pending_critical_path(kickoff_id)
    external = graph.external_dependencies(kickoff_id)

    click.echo(f"# Directed mainline (internal only) from {start}")
    for u in directed:
        click.echo(f"  - {u} [{graph.units_by_id[u].status}]")

    click.echo(f"\nCompletion (internal mainline): {completion*100:.1f}%")

    click.echo(f"\nDirected pending critical path (internal):")
    if critical:
        for u in critical:
            click.echo(f"  -> {u} [{graph.units_by_id[u].status}]")
    else:
        click.echo("  (no pending critical path)")

    click.echo(f"\nWeakly connected mainline (internal + external) from {start}:")
    for u in weak:
        tag = "internal" if graph.is_internal(u) else "external"
        status = graph.units_by_id[u].status if graph.is_internal(u) else "unknown"
        click.echo(f"  - {u} [{tag}] [{status}]")

    click.echo(f"\nExternal dependencies in this component:")
    if external:
        for u in external:
            click.echo(f"  - {u}")
    else:
        click.echo("  (none)")


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