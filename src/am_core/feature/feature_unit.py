from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional, Tuple, Dict
import inspect

# ---------------------------------------------------------
# Identity key: (sourcefile, qualname)
# ---------------------------------------------------------

def get_fn_key(fn: Callable) -> Tuple[Optional[str], str]:
    source = inspect.getsourcefile(fn)
    qual = fn.__qualname__
    return (source, qual)

@dataclass
class FeatureUnit:
    fn: Callable
    id: str
    display_name: Optional[str] = None
    status: str = "pending"
    belongs_to: List[str] = field(default_factory=list)
    depends_on: List[Callable] = field(default_factory=list)  # symbol-based
    due: Optional[datetime] = None
    scheduled: Optional[datetime] = None
    estimate: Optional[float] = None
    priority: Optional[int] = None
    notes: Optional[str] = None
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def effective_name(self):
        return self.display_name or f"{self.fn.__module__}.{self.fn.__qualname__}"
    
FEATURE_UNITS: Dict[Tuple[Optional[str], str], FeatureUnit] = {}


def feature_unit(
    *,
    id: Optional[str] = None,
    display_name: Optional[str] = None,
    status: Optional[str] = None,
    belongs_to: Optional[List[str]] = None,
    depends: Optional[List[Callable]] = None,
    due: Optional[datetime] = None,
    scheduled: Optional[datetime] = None,
    estimate: Optional[float] = None,
    priority: Optional[int] = None,
    notes: Optional[str] = None,
    weight: float = 1.0,
):
    belongs_to = belongs_to or []
    depends = depends or []

    def decorator(fn):
        key = get_fn_key(fn)
        unit_id = id or f"{fn.__module__}.{fn.__qualname__}"

        if key not in FEATURE_UNITS:
            FEATURE_UNITS[key] = FeatureUnit(
                fn=fn,
                id=unit_id,
                display_name=display_name,
                status=status or "pending",
                belongs_to=belongs_to,
                depends_on=depends,
                due=due,
                scheduled=scheduled,
                estimate=estimate,
                priority=priority,
                notes=notes,
                weight=weight,
            )
        return fn

    return decorator
