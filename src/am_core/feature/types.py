from datetime import datetime, timedelta
from types import FunctionType
from typing import Literal

TimeName4Unit = Literal["start", "end", "created_at", "completed_at"]
TimeExpr = datetime | tuple[FunctionType | str, TimeName4Unit, int]
DurationExpr = timedelta | tuple[FunctionType | str, Literal["duration"], int]