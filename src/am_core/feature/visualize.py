import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List
from .feature_unit import FeatureUnit
from .graph import FeatureUnitGraph, STATUS_COLOR


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
    units.sort(key=lambda u: u.scheduled)

    fig, ax = plt.subplots(figsize=figsize)

    for i, u in enumerate(units):
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

    # Sort by scheduled date
    units.sort(key=lambda u: u.scheduled)

    fig, ax = plt.subplots(figsize=figsize)

    for i, u in enumerate(units):
        start = mdates.date2num(u.scheduled).item()
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