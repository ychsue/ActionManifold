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

import argparse
from am_core.feature.collector import collect_feature_units
from am_core.feature.graph import FeatureUnitGraph
from am_core.feature.report import generate_roadmap
from am_core.feature.visualize import visualize_timeline, visualize_gantt


# ------------------------------------------------------------
# Helper: Build graph from root directory
# ------------------------------------------------------------
def build_graph_from_root(root_path: str) -> FeatureUnitGraph:
    units = collect_feature_units(root_path)
    return FeatureUnitGraph(units)


# ------------------------------------------------------------
# Commands
# ------------------------------------------------------------
def cmd_roadmap(args):
    graph = build_graph_from_root(args.root)
    generate_roadmap(graph, args.output)
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


# ------------------------------------------------------------
# Main CLI
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="am",
        description="ActionManifold Development Semantics CLI"
    )
    sub = parser.add_subparsers(dest="command")

    # roadmap
    p_roadmap = sub.add_parser("roadmap", help="Generate roadmap.md")
    p_roadmap.add_argument("--root", required=True, help="Root directory of project")
    p_roadmap.add_argument("--output", default="roadmap.md")
    p_roadmap.set_defaults(func=cmd_roadmap)

    # graph
    p_graph = sub.add_parser("graph", help="Visualize dependency graph")
    p_graph.add_argument("--root", required=True)
    p_graph.add_argument("--pending", action="store_true")
    p_graph.set_defaults(func=cmd_graph)

    # timeline
    p_timeline = sub.add_parser("timeline", help="Visualize timeline")
    p_timeline.add_argument("--root", required=True)
    p_timeline.add_argument("--pending", action="store_true")
    p_timeline.set_defaults(func=cmd_timeline)

    # gantt
    p_gantt = sub.add_parser("gantt", help="Visualize Gantt chart")
    p_gantt.add_argument("--root", required=True)
    p_gantt.add_argument("--pending", action="store_true")
    p_gantt.set_defaults(func=cmd_gantt)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()