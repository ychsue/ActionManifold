from typing import List
from datetime import datetime
from .graph import FeatureUnitGraph
from .feature_unit import FeatureUnit

def generate_roadmap(graph: FeatureUnitGraph, filepath: str):
    """
    Generate a full roadmap.md file summarizing:
      - development overview
      - feature coverage
      - development order
      - pending shortest path
      - pending critical path
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

    # Try to compute paths
    try:
        pending_cp = graph.pending_critical_path()
    except Exception:
        pending_cp = []

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
    # Pending critical path
    # ------------------------------------------------------------
    lines.append("## 🔥 Current Critical Path (Pending Only)\n")
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
                lines.append(f"  - {d}")
    else:
        lines.append("No blocked units.\n")

    lines.append("")

    # ------------------------------------------------------------
    # Write file
    # ------------------------------------------------------------
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))