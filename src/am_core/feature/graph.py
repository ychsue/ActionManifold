import networkx as nx
from typing import List, Dict
from .feature_unit import FeatureUnit

STATUS_COLOR = {
    "done": "green",
    "planned": "orange",
    "imagined": "gray"
}

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
        self.graph = nx.DiGraph()
        self._build_graph()

    # ------------------------------------------------------------
    # Build graph
    # ------------------------------------------------------------
    def _build_graph(self):
        for u in self.units:
            self.graph.add_node(
                u.id,
                unit=u,
                color=STATUS_COLOR.get(u.status, "black"),
                weight=u.weight
            )

        for u in self.units:
            for dep in u.depends_on:
                self.graph.add_edge(dep, u.id)

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

    # ------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------
    def visualize(self, figsize=(12, 8), pending=False):
        import matplotlib.pyplot as plt

        G = self._pending_graph() if pending else self.graph
        pos = nx.spring_layout(G, seed=42)

        node_colors = [G.nodes[n]["color"] for n in G.nodes]
        node_sizes = [G.nodes[n]["weight"] * 800 for n in G.nodes]

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
    def _is_done(self, unit_id: str) -> bool:
        for u in self.units:
            if u.id == unit_id:
                return u.status == "done"
        return False