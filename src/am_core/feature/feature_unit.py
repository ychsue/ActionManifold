from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Tuple, Dict
import inspect
import builtins

from .types import TimeExpr, TimeName4Unit

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
    due: Optional[datetime|TimeExpr] = None
    scheduled: Optional[datetime|TimeExpr] = None
    duration: Optional[timedelta] = None
    start: Optional[datetime] = None # computed
    end: Optional[datetime] = None   # computed
    estimate: Optional[float] = None
    priority: Optional[int] = None
    notes: Optional[str] = None
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def effective_name(self):
        return self.display_name or f"{self.fn.__module__}.{self.fn.__qualname__}"
    
# 使用 builtins 避免 reload 重置
if not hasattr(builtins, 'FEATURE_UNITS'):
    builtins.FEATURE_UNITS: Dict[Tuple[Optional[str], str], FeatureUnit] = {}  # type: ignore[attr-defined]
FEATURE_UNITS: Dict[Tuple[Optional[str], str], FeatureUnit] = builtins.FEATURE_UNITS  # type: ignore[attr-defined]

if not hasattr(builtins, 'IMPORTED_FEATURE_UNIT_MODULES'):
    builtins.IMPORTED_FEATURE_UNIT_MODULES: set = set()  # type: ignore[attr-defined]
IMPORTED_FEATURE_UNIT_MODULES: set = builtins.IMPORTED_FEATURE_UNIT_MODULES  # type: ignore[attr-defined]

def feature_unit(
    *,
    id: Optional[str] = None,
    display_name: Optional[str] = None,
    status: Optional[str] = None,
    belongs_to: Optional[List[str]] = None,
    depends: Optional[List[Callable]] = None,
    due: Optional[datetime|TimeExpr] = None,
    scheduled: Optional[datetime|TimeExpr] = None,
    duration: Optional[timedelta] = None,
    estimate: Optional[float] = None,
    priority: Optional[int] = None,
    notes: Optional[str] = None,
    weight: float = 1.0,
):
    belongs_to = belongs_to or []
    depends = depends or []

    def decorator(fn):
        # 在還沒有正式開始collecting之前，不要註冊feature units
        if len(IMPORTED_FEATURE_UNIT_MODULES) == 0:
            return fn
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
                duration=duration,
                estimate=estimate,
                priority=priority,
                notes=notes,
                weight=weight,
            )
            print(f"Created FeatureUnit: {unit_id}")  # Add this line
        else:
            print(f"FeatureUnit already exists: {unit_id}")  # Add this line
        print(f"Current FEATURE_UNITS length: {len(FEATURE_UNITS)}")  # Add this line

        return fn

    return decorator
