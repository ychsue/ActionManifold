from typing import List, Optional
from datetime import datetime
from ..graph import FeatureUnitGraph
from .feature_unit import FeatureUnit, feature_unit

@feature_unit(
    belongs_to=["DevEngine"],
    status="done",
    display_name="Generate Development Roadmap",
    depends=[FeatureUnitGraph, FeatureUnitGraph.development_order, FeatureUnitGraph.pending_critical_path],
    notes="產生 roadmap.md，整合 overview / coverage / mainline / blockers / ready"
)
def generate_roadmap(graph: FeatureUnitGraph, filepath: str, kickoff: Optional[str] = None):
    """
    Generate a full roadmap.md file summarizing:
      - development overview
      - feature coverage
      - development order
      - directed mainline (internal)
      - weakly connected mainline (internal + external)
      - mainline completion
      - pending critical path
      - external dependencies
      - blocked units
      - ready units
    """

    units = graph.units

    done = [u for u in units if u.status == "done"]
    planned = [u for u in units if u.status == "planned"]
    imagined = [u for u in units if u.status == "imagined"]

    blocked = graph.blocked_units()
    ready = graph.ready_units()
    coverage = graph.feature_coverage()

    # Try to compute pending critical path
    try:
        pending_cp = graph.pending_critical_path()
    except Exception:
        pending_cp = []

    # If kickoff is provided, compute mainlines
    if kickoff:
        directed_mainline = graph.directed_mainline(kickoff)
        weak_mainline = graph.weakly_connected_mainline(kickoff)
        external = graph.external_dependencies(kickoff)
        completion = graph.mainline_completion(kickoff)
        directed_cp = graph.directed_pending_critical_path(kickoff)
    else:
        directed_mainline = []
        weak_mainline = []
        external = set()
        completion = None
        directed_cp = []

    # Build markdown
    lines = []

    lines.append("# 🧭 Development Roadmap\n")
    lines.append(f"Generated at: **{datetime.now().isoformat()}**\n")

    # ------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------
    lines.append("## 📌 Overview\n")
    lines.append(f"- Total units: **{len(units)}**")
    lines.append(f"- Done: **{len(done)}**")
    lines.append(f"- Planned: **{len(planned)}**")
    lines.append(f"- Imagined: **{len(imagined)}**")
    lines.append(f"- Ready to start: **{len(ready)}**")
    lines.append(f"- Blocked: **{len(blocked)}**\n")

    # ------------------------------------------------------------
    # Feature coverage
    # ------------------------------------------------------------
    lines.append("## 🗂 Feature Coverage\n")
    for feature, unit_ids in coverage.items():
        lines.append(f"### {feature}")
        for uid in unit_ids:
            u = next(x for x in units if x.id == uid)
            lines.append(f"- {uid} ({u.status})")
        lines.append("")

    # ------------------------------------------------------------
    # Development order
    # ------------------------------------------------------------
    lines.append("## 🧱 Suggested Development Order\n")
    try:
        order = graph.development_order()
        for i, uid in enumerate(order, 1):
            u = next(x for x in units if x.id == uid)
            lines.append(f"{i}. {uid} ({u.status})")
    except Exception:
        lines.append("⚠️ Cannot compute development order due to dependency cycle.\n")

    lines.append("")

    # ------------------------------------------------------------
    # Directed mainline (internal)
    # ------------------------------------------------------------
    if kickoff:
        lines.append(f"## 🛣 Directed Mainline (Internal Only)\nStart: **{kickoff}**\n")
        if directed_mainline:
            for uid in directed_mainline:
                u = graph.units_by_id[uid]
                lines.append(f"- {uid} ({u.status})")
        else:
            lines.append("No directed mainline found.\n")
        lines.append("")

        # Completion
        lines.append("### 🎯 Mainline Completion\n")
        # 若 completion 是 None，表示無法計算主線完成度
        if completion is None:
            lines.append("Cannot compute mainline completion due to dependency cycle.\n")
        else:
            lines.append(f"- **{completion*100:.1f}%** complete\n")
        lines.append("")

        # Directed pending critical path
        lines.append("### 🔥 Directed Pending Critical Path\n")
        if directed_cp:
            for uid in directed_cp:
                u = graph.units_by_id[uid]
                lines.append(f"- {uid} ({u.status})")
        else:
            lines.append("No pending critical path.\n")
        lines.append("")

    # ------------------------------------------------------------
    # Weakly connected mainline (internal + external)
    # ------------------------------------------------------------
    if kickoff:
        lines.append("## 🌐 Weakly Connected Mainline (Internal + External)\n")
        for uid in weak_mainline:
            tag = "internal" if graph.is_internal(uid) else "external"
            status = graph.units_by_id[uid].status if graph.is_internal(uid) else "unknown"
            lines.append(f"- {uid} [{tag}] ({status})")
        lines.append("")

        # External dependencies
        lines.append("### 🌍 External Dependencies\n")
        if external:
            for uid in external:
                lines.append(f"- {uid}")
        else:
            lines.append("No external dependencies.\n")
        lines.append("")

    # ------------------------------------------------------------
    # Pending critical path (global)
    # ------------------------------------------------------------
    lines.append("## 🔥 Global Pending Critical Path\n")
    if pending_cp:
        for uid in pending_cp:
            u = next(x for x in units if x.id == uid)
            lines.append(f"- {uid} ({u.status})")
    else:
        lines.append("No pending critical path.\n")

    lines.append("")

    # ------------------------------------------------------------
    # Ready units
    # ------------------------------------------------------------
    lines.append("## ✅ Ready to Start\n")
    if ready:
        for u in ready:
            lines.append(f"- {u.id}")
    else:
        lines.append("No units ready.\n")

    lines.append("")

    # ------------------------------------------------------------
    # Blocked units
    # ------------------------------------------------------------
    lines.append("## ⛔ Blocked Units\n")
    if blocked:
        for uid, deps in blocked.items():
            lines.append(f"- **{uid}** blocked by:")
            for d in deps:
                stBlocked = f"  - {d}".replace("<", "&lt;").replace(">", "&gt;")
                lines.append(stBlocked)
    else:
        lines.append("No blocked units.\n")

    lines.append("")

    # ------------------------------------------------------------
    # Write file
    # ------------------------------------------------------------
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))