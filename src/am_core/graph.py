from math import e
from types import FunctionType
import networkx as nx
from typing import List, Dict, Set

from torch import ne
from .feature.feature_unit import FeatureUnit
from .feature.feature_unit import feature_unit, get_fn_key

STATUS_COLOR = {
    "done": "green",
    "planned": "orange",
    "imagined": "gray",
    "pending": "red",
}

@feature_unit(
    belongs_to=["DevEngine"],
    status="done",
    notes="建立 FeatureUnit 的語意圖，支援依賴分析與視覺化",
)
class FeatureUnitGraph:
    """
    A semantic graph of FeatureUnits.
    Supports:
      - cycle detection
      - development order (topological)
      - pending graph (excluding done)
      - shortest path / critical path
      - pending shortest / pending critical path
      - feature coverage
      - visualization
    """

    def __init__(self, units: List[FeatureUnit]):
        self.units = units
        self.units_by_id: Dict[str, FeatureUnit] = {u.id: u for u in units}
        self.graph = nx.DiGraph()
        self._build_graph()

    def to_mermaid(self, for_markdown: bool = True) -> str:
        if for_markdown:
            lines = ["```mermaid"]
        else:
            lines = []
        lines.append("graph TD")

        for u in self.units:
            node_id = u.id.replace(".", "_")
            label = u.effective_name.replace('.', ' ')
            color = STATUS_COLOR.get(u.status, "#AAAAAA")

            # 節點
            lines.append(f'    {node_id}["{label}"]')

            # 顏色
            lines.append(f'    style {node_id} fill:{color},stroke:#333,stroke-width:1px')
            
            # 文字顏色
            lines.append(
                f'style {node_id} fill:{color},stroke:#000000,stroke-width:2px,color:#FFFFFF,font-weight:bold'
            )

            # 邊
            for dep_fn in u.depends_on:
                dep_key = get_fn_key(dep_fn)
                dep_unit = next((x for x in self.units if get_fn_key(x.fn) == dep_key), None)
                if dep_unit:
                    dep_id = dep_unit.id.replace(".", "_")
                    lines.append(f"    {dep_id} --> {node_id}")  # 你可以換成 .-> 或 o-->

        if for_markdown:
            lines.append("```")
        return "\n".join(lines)
    # ------------------------------------------------------------
    # Build graph
    # ------------------------------------------------------------
    def _build_graph(self):
        # 先建立 function/class → FeatureUnit 的索引
        key_to_unit = {get_fn_key(u.fn): u for u in self.units}
        fun_without_unit = []

        for u in self.units:
            self.graph.add_node(
                u.id,
                unit=u,
                color=STATUS_COLOR.get(u.status, "black"),
                weight=u.weight
            )

        # 再加 edge
        for u in self.units:
            for dep_fn in u.depends_on:
                dep_key = get_fn_key(dep_fn)
                dep_unit = key_to_unit.get(dep_key)
                if not dep_unit:
                    # 這裡你可以選擇：警告、忽略、或 raise TODO TODO TODO
                    print(f"[warn] depends_on 指到未知 fn: {dep_fn}")
                    fun_without_unit.append(dep_fn)
                    continue

                self.graph.add_edge(dep_unit.id, u.id)
                
        # 處理沒有對應 FeatureUnit 的 function/class
        for fn in fun_without_unit:
            fn_key = get_fn_key(fn)
            node_id = f"external_{fn_key[-1]}"
            new_unit = FeatureUnit(
                id=node_id,fn=fn,display_name=f"External {fn_key[-1]}",belongs_to=["external"],status="unknown",notes="External dependency")
            self.units.append( new_unit )
            if node_id not in self.graph:
                self.graph.add_node(
                    node_id,
                    unit=new_unit,
                    color="lightgray",
                    weight=0.5
                )

    # ------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------
    def find_cycles(self):
        try:
            return list(nx.find_cycle(self.graph, orientation="original"))
        except nx.NetworkXNoCycle:
            return []

    # ------------------------------------------------------------
    # Development order
    # ------------------------------------------------------------
    def development_order(self) -> List[str]:
        if self.find_cycles():
            raise ValueError("Dependency cycle detected")
        return list(nx.topological_sort(self.graph))

    # ------------------------------------------------------------
    # Pending graph (remove done nodes)
    # ------------------------------------------------------------
    def _pending_graph(self):
        G = self.graph.copy()
        for u in self.units:
            if u.status == "done":
                if u.id in G:
                    G.remove_node(u.id)
        return G

    # ------------------------------------------------------------
    # Shortest path (global)
    # ------------------------------------------------------------
    def shortest_path(self, start: str, end: str) -> List[str]:
        return nx.shortest_path(self.graph, start, end)

    # ------------------------------------------------------------
    # Critical path (global)
    # ------------------------------------------------------------
    def critical_path(self) -> List[str]:
        return nx.dag_longest_path(self.graph)

    # ------------------------------------------------------------
    # Pending shortest path
    # ------------------------------------------------------------
    def pending_shortest_path(self, start: str, end: str) -> List[str]:
        G = self._pending_graph()
        return nx.shortest_path(G, start, end)

    # ------------------------------------------------------------
    # Pending critical path
    # ------------------------------------------------------------
    def pending_critical_path(self) -> List[str]:
        G = self._pending_graph()
        return nx.dag_longest_path(G)

    # ------------------------------------------------------------
    # Ready units
    # ------------------------------------------------------------
    def ready_units(self) -> List[FeatureUnit]:
        ready = []
        for u in self.units:
            if u.status == "done":
                continue

            unmet = [
                dep for dep in u.depends_on
                if not self._is_done(dep)
            ]

            if not unmet:
                ready.append(u)

        return ready

    # ------------------------------------------------------------
    # Blocked units
    # ------------------------------------------------------------
    def blocked_units(self) -> Dict[str, List[str]]:
        blocked = {}
        for u in self.units:
            unmet = [
                dep for dep in u.depends_on
                if not self._is_done(dep)
            ]
            if unmet:
                blocked[u.id] = unmet
        return blocked

    # ------------------------------------------------------------
    # Feature coverage
    # ------------------------------------------------------------
    def feature_coverage(self) -> Dict[str, List[str]]:
        coverage = {}
        for u in self.units:
            for f in u.belongs_to:
                coverage.setdefault(f, []).append(u.id)
        return coverage

    # -----------------------------
    # Internal / External helpers
    # -----------------------------
    def internal_ids(self) -> Set[str]:
        return set(self.units_by_id.keys())

    def is_internal(self, unit_id: str) -> bool:
        return unit_id in self.units_by_id

    # -----------------------------
    # Directed mainline（專案生命週期）
    # -----------------------------
    def reachable_from(self, start: str) -> List[str]:
        if start not in self.graph:
            return []
        desc = nx.descendants(self.graph, start)
        return [start, *sorted(desc)]

    @feature_unit(
        belongs_to=["DevEngine"],
        status="done",
        notes="計算從 kickoff 出發的 internal 主線（有方向）",
    )
    def directed_mainline(self, start: str) -> List[str]:
        """
        Return internal-only mainline reachable from start.
        """
        # 只保留 internal nodes
        return [u for u in self.reachable_from(start) if self.is_internal(u)]

    # -----------------------------
    # Weakly connected mainline（語意宇宙）
    # -----------------------------
    @feature_unit(
        belongs_to=["DevEngine"],
        status="done",
        notes="計算包含 internal + external 的弱連通主線（語意宇宙）",
    )
    def weakly_connected_mainline(self, start: str) -> List[str]:
        """
        Return weakly connected component containing start.
        """
        if start not in self.graph:
            return []
        undirected = self.graph.to_undirected()
        for comp in nx.connected_components(undirected):
            if start in comp:
                return sorted(comp)
        return []

    # -----------------------------
    # External dependencies / blockers
    # -----------------------------
    def external_dependencies(self, start: str) -> Set[str]:
        wc = self.weakly_connected_mainline(start)
        return {u for u in wc if not self.is_internal(u)}

    def external_blockers(self, start: str) -> Set[str]:
        # 這裡假設 external 的狀態無法從這個 graph 得知
        # 先單純回傳 external_dependencies，之後可接上外部狀態來源
        return self.external_dependencies(start)

    # -----------------------------
    # Completion（只算 internal）
    # -----------------------------
    @feature_unit(
        belongs_to=["DevEngine"],
        status="done",
        depends=[directed_mainline],
        notes="計算 internal 主線的完成度（done / total）",
    )
    def mainline_completion(self, start: str) -> float:
        """
        Compute completion ratio for directed mainline.
        """
        main = self.directed_mainline(start)
        if not main:
            return 0.0
        done = [u for u in main if self.units_by_id[u].status == "done"]
        return len(done) / len(main)

    # -----------------------------
    # Directed critical path（只算 internal + pending）
    # -----------------------------
    def directed_pending_critical_path(self, start: str) -> List[str]:
        main = self.directed_mainline(start)
        pending = {u for u in main if self.units_by_id[u].status != "done"}
        if not pending:
            return []

        sub = self.graph.subgraph(pending).copy()
        sub = nx.DiGraph(sub)
        # 只保留 pending 子圖中從 start 可達的部分
        if start in sub:
            reachable = nx.descendants(sub, start) | {start}
            sub = sub.subgraph(reachable).copy()
            sub = nx.DiGraph(sub)

        if not nx.is_directed_acyclic_graph(sub):
            return []

        try:
            return nx.dag_longest_path(sub)
        except nx.NetworkXNoPath:
            return []

    # ------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------
    def visualize(self, figsize=(12, 8), pending=False):
        import matplotlib.pyplot as plt

        G = self._pending_graph() if pending else self.graph
        pos = nx.spring_layout(G, seed=42)

        node_colors = [
            G.nodes[n].get("color", "lightgray")   # external nodes default
            for n in G.nodes
        ]

        node_sizes = [
            G.nodes[n].get("weight", 0.5) * 800    # external nodes default
            for n in G.nodes
        ]
        
        plt.figure(figsize=figsize)
        nx.draw_networkx(
            G,
            pos,
            with_labels=True,
            node_color=node_colors,
            node_size=node_sizes,
            font_size=8,
            arrows=True
        )
        plt.show()

    # ------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------
    def _is_done(self, unit_id: FunctionType) -> bool:
        for u in self.units:
            if u.id == unit_id:
                return u.status == "done"
        return False