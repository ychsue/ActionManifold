from datetime import datetime, timedelta
from types import FunctionType
from typing import Literal
import logging

from attr import field

from am_core.graph import FeatureUnitGraph
from .feature_unit import FeatureUnit, get_fn_key
from .types import TimeName4Unit, TimeExpr, DurationExpr
def resolve_time(expr: TimeExpr, graph: FeatureUnitGraph):
    # 1. 絕對時間
    if isinstance(expr, datetime):
        return expr

    # 2. 相對時間
    if not isinstance(expr, tuple) or len(expr) != 3:
        raise ValueError(f"Invalid time expression format: {expr}")
    
    fun_or_id, field_name, offset = expr

    # fun → key
    ref_unit: FeatureUnit
    if isinstance(fun_or_id, FunctionType):
        refs = [unit for unit in graph.units if unit.fn == fun_or_id]
        if not refs:
            raise ValueError(f"Function {fun_or_id} not found in graph.")
        ref_unit = refs[0]
    else:
        ref_unit = graph.units_by_id[fun_or_id]

    base_time = getattr(ref_unit, field_name)
    if not isinstance(base_time, datetime):
        raise TypeError(f"Field '{field_name}' is not a datetime: {base_time}")

    return base_time + timedelta(days=offset)

def resolve_duration(expr: DurationExpr, graph: FeatureUnitGraph):
    # 1. 絕對 duration
    if isinstance(expr, timedelta):
        return expr

    # 2. 相對 duration
    if not isinstance(expr, tuple) or len(expr) != 3:
        raise ValueError(f"Invalid duration expression format: {expr}")
    
    fun_or_id, field, offset = expr

    # fun → key
    ref_unit: FeatureUnit
    if isinstance(fun_or_id, FunctionType):
        refs = [unit for unit in graph.units if unit.fn == fun_or_id]
        if not refs:
            raise ValueError(f"Function {fun_or_id} not found in graph.")
        ref_unit = refs[0]
    else:
        ref_unit = graph.units_by_id[fun_or_id]

    base_duration = getattr(ref_unit, field)
    if not isinstance(base_duration, timedelta):
        raise TypeError(f"Field '{field}' is not a timedelta: {base_duration}")

    return base_duration + timedelta(days=offset)

def resolve_unit_times(unit: FeatureUnit, graph: FeatureUnitGraph, visited=None):
    if visited is None:
        visited = set()
    if unit.id in visited:
        raise ValueError(f"Circular dependency detected for unit {unit.id}")
    visited.add(unit.id)

    # 展開 scheduled
    scheduled = resolve_time(unit.scheduled, graph) if unit.scheduled else None

    # 展開 duration
    duration = resolve_duration(unit.duration, graph) if unit.duration else None

    # 展開 due
    due = resolve_time(unit.due, graph) if unit.due else None

    # 規則 1：scheduled + duration → due
    if scheduled and duration:
        if due:
            # 已有 due，警告
            logging.warning(f"Unit {unit.id} already has due date set. Overwriting due date.")
        due = scheduled + duration

    # 規則 2：scheduled + due → duration
    elif scheduled and due:
        duration = due - scheduled
        unit.duration = duration

    # 規則 3：只有 duration → scheduled = max(depends.end)
    elif duration and unit.depends_on:
        # 由 depends_on 的函數本身找出對應的 FeatureUnit
        fus = []
        for dep_fn in unit.depends_on:
            dep_key = get_fn_key(dep_fn)
            dep_fu = next((fu for fu in graph.units if get_fn_key(fu.fn) == dep_key), None)
            if dep_fu:
                fus.append(dep_fu)
        if not fus:
            raise ValueError(f"No valid dependencies found for unit {unit.id}")
        dep_ends = [resolve_unit_times(dep, graph, visited.copy()).end for dep in fus]
        max_end = max((end for end in dep_ends if end is not None), default=None)
        if max_end is None:
            raise ValueError(f"No end times available for dependencies of unit {unit.id}")
        scheduled = max_end
        due = scheduled + duration
        unit.scheduled = scheduled
        unit.due = due

    # 規則 4：只有 due → scheduled = due - duration
    elif due and duration:
        scheduled = due - duration
        unit.scheduled = scheduled

    # 最終 start/end
    unit.start = scheduled
    unit.end = due
    
    visited.remove(unit.id)
    return unit