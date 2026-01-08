import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List
from .feature_unit import FeatureUnit, feature_unit
from ..graph import FeatureUnitGraph, STATUS_COLOR

@feature_unit(
    belongs_to=["DevEngine"],
    status="done",
    display_name="Visualize FeatureUnit Timeline",
    depends=[FeatureUnitGraph],
    notes="依 scheduled → due 畫出時間線，可選 pending-only"
)
def visualize_timeline(graph: FeatureUnitGraph, figsize=(14, 6), pending=False):
    """
    Draw a timeline of FeatureUnits based on scheduled → due dates.
    If pending=True, exclude units with status == done.
    """

    units = graph.units
    if pending:
        units = [u for u in units if u.status != "done"]

    # Filter units that have scheduled/due dates
    units = [u for u in units if u.scheduled and u.due]
    if not units:
        print("No units with scheduled/due dates to visualize.")
        return

    # Sort by scheduled date
    units.sort(key=lambda u: u.scheduled or datetime.max)

    fig, ax = plt.subplots(figsize=figsize)

    for i, u in enumerate(units):
        # 若沒有 due or scheduled，條列出來當作 legend
        if not u.due or not u.scheduled:
            ax.plot([], [], color=STATUS_COLOR.get(u.status, "gray"), linewidth=4, label=f"{u.id} ({u.status})")
            continue
        start = mdates.date2num(u.scheduled).item()
        end = mdates.date2num(u.due).item()
        ax.plot([start, end], [i, i], color=STATUS_COLOR.get(u.status, "black"), linewidth=4)
        ax.text(start, i + 0.1, u.id, fontsize=8)

    ax.set_yticks(range(len(units)))
    ax.set_yticklabels([u.id for u in units])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.title("FeatureUnit Timeline" + (" (Pending Only)" if pending else ""))
    plt.tight_layout()
    plt.show()

@feature_unit(
    belongs_to=["DevEngine"],
    status="done",
    display_name="Visualize FeatureUnit Gantt Chart",
    depends=[FeatureUnitGraph],
    notes="以 Gantt 圖呈現 FeatureUnit 的排程與狀態"
)
def visualize_gantt(graph: FeatureUnitGraph, figsize=(14, 8), pending=False):
    """
    Draw a Gantt chart for FeatureUnits.
    """

    units = graph.units
    if pending:
        units = [u for u in units if u.status != "done"]

    # Only units with scheduled/due
    units = [u for u in units if u.scheduled and u.due]
    if not units:
        print("No units with scheduled/due dates to visualize.")
        return

    # Sort by scheduled date. If no scheduled, put at the end
    units.sort(key=lambda u: u.scheduled or datetime.max)

    fig, ax = plt.subplots(figsize=figsize)

    for i, u in enumerate(units):
        start = mdates.date2num(u.scheduled).item()
        # 若沒有 due or scheduled，當作 legend
        if not u.due or not u.scheduled:
            ax.barh(
                y=i,
                width=1,
                left=start,
                color=STATUS_COLOR.get(u.status, "gray"),
                edgecolor="black"
            )
            ax.text(start, i, f" {u.id}", va="center", fontsize=8)
            continue
        duration = (u.due - u.scheduled).days
        ax.barh(
            y=i,
            width=duration,
            left=start,
            color=STATUS_COLOR.get(u.status, "gray"),
            edgecolor="black"
        )
        ax.text(start, i, f" {u.id}", va="center", fontsize=8)

    ax.set_yticks(range(len(units)))
    ax.set_yticklabels([u.id for u in units])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.title("FeatureUnit Gantt Chart" + (" (Pending Only)" if pending else ""))
    plt.tight_layout()
    plt.show()