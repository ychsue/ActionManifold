# src/am_server/engine.py

from typing import List, Dict
from .models import FeatureUnitModel, GraphModel

# ---------------------------------------------------------
# 這裡是「假的 AM 引擎」，只是為了讓 API 可以跑起來
# 未來你會把真正的 ActionManifold 核心接進來
# ---------------------------------------------------------

# 假資料：你未來會從 FeatureUnit registry 取得
_FAKE_FEATURES = {
    "build": FeatureUnitModel(
        name="build",
        summary="Build the project",
        description="Compile and prepare artifacts",
        inputs=[],
        outputs=["dist/"],
        deps=["clean"]
    ),
    "clean": FeatureUnitModel(
        name="clean",
        summary="Clean build artifacts",
        description="Remove dist/ and temp files",
        inputs=[],
        outputs=[],
        deps=[]
    ),
}

def describe_all() -> List[FeatureUnitModel]:
    return list(_FAKE_FEATURES.values())

def build_graph() -> GraphModel:
    nodes = list(_FAKE_FEATURES.keys())
    edges = []
    for name, fu in _FAKE_FEATURES.items():
        for dep in fu.deps:
            edges.append((dep, name))
    return GraphModel(nodes=nodes, edges=edges)

def get_dependencies(feature: str) -> List[str]:
    if feature not in _FAKE_FEATURES:
        return []
    return _FAKE_FEATURES[feature].deps

def run(feature: str):
    if feature not in _FAKE_FEATURES:
        return None, ["Feature not found"]

    logs = [
        f"Running feature: {feature}",
        "Executing steps...",
        "Done."
    ]
    return f"Feature {feature} executed.", logs