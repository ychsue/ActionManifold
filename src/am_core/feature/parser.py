import inspect
import re
from typing import Optional
from .feature_unit import FeatureUnit
from datetime import datetime, timedelta

UNIT_RE = re.compile(r"@unit\s+(.+)")
STATUS_RE = re.compile(r"@status\s+(.+)")
FEATURE_RE = re.compile(r"@feature\s+(.+)")
DEPENDS_RE = re.compile(r"@depends\s+(.+)")
NOTES_RE = re.compile(r"@notes\s+(.+)")
WEIGHT_RE = re.compile(r"@weight\s+([\d.]+)")
DUE_RE = re.compile(r"@due\s+(.+)")
SCHEDULED_RE = re.compile(r"@scheduled\s+(.+)")
ESTIMATE_RE = re.compile(r"@estimate\s+([\d.]+)")
PRIORITY_RE = re.compile(r"@priority\s+(\d+)")

def parse_feature_unit(method) -> Optional[FeatureUnit]:
    """
    Parse FeatureUnit metadata from a method's docstring.
    Returns FeatureUnit or None if no @unit tag is found.
    """
    doc = inspect.getdoc(method)
    if not doc:
        return None

    lines = doc.splitlines()

    unit_id = None
    status = None
    features = []
    depends = []
    notes = None
    weight = None
    due: Optional[datetime] = None
    scheduled: Optional[datetime] = None
    estimate: Optional[float] = None
    priority: Optional[int] = None

    for line in lines:
        line = line.strip()

        if m := UNIT_RE.match(line):
            unit_id = m.group(1).strip()
        elif m := STATUS_RE.match(line):
            status = m.group(1).strip()
        elif m := FEATURE_RE.match(line):
            features.append(m.group(1).strip())
        elif m := DEPENDS_RE.match(line):
            depends.append(m.group(1).strip())
        elif m := NOTES_RE.match(line):
            notes = m.group(1).strip()
        elif m := WEIGHT_RE.match(line):
            weight = float(m.group(1).strip())
        elif m := DUE_RE.match(line):
            due_str = m.group(1).strip()
            due = datetime.strptime(due_str, "%Y-%m-%d")
        elif m := SCHEDULED_RE.match(line):
            scheduled_str = m.group(1).strip()
            scheduled = datetime.strptime(scheduled_str, "%Y-%m-%d")
        elif m := ESTIMATE_RE.match(line):
            estimate = float(m.group(1).strip())
        elif m := PRIORITY_RE.match(line):
            priority = int(m.group(1).strip())

    if not unit_id:
        return None

    # 以下兩個欄位給預設值 TODO 改進
    if not due:
        due = datetime.now()+ timedelta(days=365)  # Default due date in 1 year
    if not scheduled:
        scheduled = datetime.now() + timedelta(days=364)  # Default scheduled date is today
    
    return FeatureUnit(
        id=unit_id,
        status=status or "planned",
        belongs_to=features,
        depends_on=depends,
        weight=weight or 1.0,
        due=due,
        scheduled=scheduled,
        estimate=estimate,
        priority=priority,
        notes=notes
    )