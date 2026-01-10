from pydantic import BaseModel
from typing import List, Optional

class FeatureUnitModel(BaseModel):
    name: str
    summary: Optional[str] = None
    description: Optional[str] = None
    inputs: List[str] = []
    outputs: List[str] = []
    deps: List[str] = []
    
class GraphModel(BaseModel):
    nodes: List[str]
    edges: List[tuple[str, str]]
    
class CommandModel(BaseModel):
    name: str
    summary: str
    
class RunResultModel(BaseModel):
    feature: str
    status: str
    output: Optional[str] = None
    logs: List[str] = []
    