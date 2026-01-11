# src/am_server/engine.py

from typing import List, Dict, Tuple
from pathlib import Path
from .models import FeatureUnitModel, GraphModel, RunResultModel
from am_core.feature.collector import collect_feature_units, get_FU_by_fn
from am_core.graph import FeatureUnitGraph
from am_core.feature.report import generate_roadmap
from am_core.feature.visualize import visualize_timeline, visualize_gantt
from am_core.feature.feature_unit import get_fn_key
import tempfile
import os

# 全域狀態，類似 main.py 中的 state
_pkg_path = str(Path.cwd().resolve())
_root_paths = ["."]

def set_pkg_path(pkg_path: str):
    global _pkg_path
    _pkg_path = pkg_path

def set_root_paths(root_paths: List[str]):
    global _root_paths
    _root_paths = root_paths

def _build_graph() -> FeatureUnitGraph:
    units = []
    for root_path in _root_paths:
        units.extend(collect_feature_units(root_path, pkg_path=_pkg_path))
    return FeatureUnitGraph(units)

def describe_all() -> List[FeatureUnitModel]:
    graph = _build_graph()
    return [
        FeatureUnitModel(
            name=u.id,
            summary=u.effective_name,
            description=u.notes or "",
            inputs=[],  # TODO: 從 unit 提取
            outputs=[],  # TODO: 從 unit 提取
            deps=[i.id for i in [get_FU_by_fn(dep, graph.units) for dep in u.depends_on] if i is not None]
        )
        for u in graph.units
    ]

def build_graph() -> GraphModel:
    graph = _build_graph()
    nodes = list(graph.units_by_id.keys())
    edges = []
    for u in graph.units:
        for dep in u.depends_on:
            dep_unit = get_FU_by_fn(dep, graph.units)
            if dep_unit:
                edges.append((dep_unit.id, u.id))
    return GraphModel(nodes=nodes, edges=edges)

def get_dependencies(feature: str) -> List[str]:
    graph = _build_graph()
    if feature not in graph.units_by_id:
        return []
    unit = graph.units_by_id[feature]
    deps = []
    for dep in unit.depends_on:
        dep_unit = get_FU_by_fn(dep, graph.units)
        if dep_unit:
            deps.append(dep_unit.id)
    return deps

def run(feature: str) -> Tuple[str, List[str]]:
    # TODO: 實現真正的運行邏輯
    # 目前只是模擬
    logs = [
        f"Running feature: {feature}",
        "Executing steps...",
        "Done."
    ]
    return f"Feature {feature} executed.", logs

def generate_md(command: str, output_path: str, **kwargs) -> str:
    """
    生成 .md 檔案的通用函數
    command: 'roadmap', 'graph', 'timeline', 'gantt', 'mainline', 'mermaid'
    """
    graph = _build_graph()

    if command == "roadmap":
        kickoff = kwargs.get("kickoff")
        generate_roadmap(graph, output_path, kickoff=kickoff)
        return f"Roadmap generated at {output_path}"

    elif command == "mermaid":
        with open(output_path, "w") as f:
            f.write(graph.to_mermaid())
        return f"Mermaid graph saved to {output_path}"

    elif command == "timeline":
        # 將 timeline 輸出到 .md
        content = "# Timeline\n\n"
        content += graph.to_mermaid_timeline(pending=kwargs.get("pending", False))
        with open(output_path, "w") as f:
            f.write(content)
        return f"Timeline generated at {output_path}"
    
    elif command == "gantt":
        # 將 gantt 輸出到 .md
        content = "# Gantt Chart\n\n"
        content += graph.to_mermaid_gantt(pending=kwargs.get("pending", False))
        return f"Gantt chart generated at {output_path}"

    elif command == "mainline":
        start = kwargs.get("start")
        if not start:
            raise ValueError("start parameter required for mainline")

        # 找出 kickoff node
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

        content = f"# Mainline Analysis from {start}\n\n"
        content += f"## Directed mainline (internal only)\n"
        for u in directed:
            content += f"- {u} [{graph.units_by_id[u].status}]\n"

        content += f"\n## Completion: {completion*100:.1f}%\n"

        content += f"\n## Directed pending critical path\n"
        if critical:
            for u in critical:
                content += f"- {u} [{graph.units_by_id[u].status}]\n"
        else:
            content += "(no pending critical path)\n"

        content += f"\n## Weakly connected mainline (internal + external)\n"
        for u in weak:
            tag = "internal" if graph.is_internal(u) else "external"
            status = graph.units_by_id[u].status if graph.is_internal(u) else "unknown"
            content += f"- {u} [{tag}] [{status}]\n"

        content += f"\n## External dependencies\n"
        if external:
            for u in external:
                content += f"- {u}\n"
        else:
            content += "(none)\n"

        with open(output_path, "w") as f:
            f.write(content)
        return f"Mainline analysis saved to {output_path}"

    else:
        raise ValueError(f"Unknown command: {command}")