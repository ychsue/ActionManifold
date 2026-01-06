from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class FeatureUnit:
    """
    FeatureUnit 的 Docstring 宣告為
    @unit <module.class.method>
    @status <done|planned|imagined>
    @feature <FeatureName>              # 可多個
    @depends <module.class.method>      # 可多個
    @due <YYYY-MM-DD>
    @scheduled <YYYY-MM-DD>
    @estimate <float hours>
    @priority <int>
    @notes <free text>
    """
    id: str
    status: str                     # done | planned | imagined
    belongs_to: List[str]
    depends_on: List[str]
    due: datetime
    scheduled: datetime
    estimate: Optional[float] = None
    priority: Optional[int] = None
    notes: Optional[str] = None
    weight: float = 1.0             # cost / difficulty / time
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None