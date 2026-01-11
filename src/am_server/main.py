# src/am_server/main.py

from dataclasses import dataclass
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from typing import List, Optional

from am_core.feature.feature_unit import feature_unit
from .models import (
    FeatureUnitModel,
    GraphModel,
    RunResultModel,
)
from . import engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ActionManifold Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定 http://localhost:8000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class State:
    pkg_path: str
    root_paths: List[str]

state = State(
    pkg_path=str(Path.cwd().resolve()),
    root_paths=["."]
)

@app.get("/commands")
def list_commands():
    return {
        "commands": [
            {"name": "describe", "summary": "Describe all FeatureUnits"},
            {"name": "graph", "summary": "Return dependency graph"},
            {"name": "deps", "summary": "List dependencies of a FeatureUnit"},
            {"name": "run", "summary": "Run a FeatureUnit"},
            {"name": "generate-md", "summary": "Generate .md file with various formats"},
        ]
    }

@app.get("/describe", response_model=List[FeatureUnitModel])
def describe():
    return engine.describe_all()

@app.get("/graph", response_model=GraphModel)
def graph():
    return engine.build_graph()

@app.get("/deps/{feature}", response_model=List[str])
def deps(feature: str):
    return engine.get_dependencies(feature)

@app.post("/run/{feature}", response_model=RunResultModel)
def run(feature: str):
    output, logs = engine.run(feature)
    return RunResultModel(
        feature=feature,
        status="ok" if output else "error",
        output=output,
        logs=logs,
    )

@app.post("/generate-md")
def generate_md(command: str, output_path: str, start: Optional[str] = None, kickoff: Optional[str] = None):
    """
    生成 .md 檔案的 API 端點
    - command: roadmap, mermaid, timeline, gantt, mainline
    - output_path: 輸出檔案路徑
    - start: 對於 mainline 命令的起始節點
    - kickoff: 對於 roadmap 命令的 kickoff 節點
    """
    try:
        kwargs = {}
        if start:
            kwargs["start"] = start
        if kickoff:
            kwargs["kickoff"] = kickoff
        
        result = engine.generate_md(command, output_path, **kwargs)
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@feature_unit(status="done")
@app.post("/config/root_paths")
def set_root_paths(root_paths: List[str] = Form(...)):
    state.root_paths = [r for r in root_paths if r.strip()]
    engine.set_root_paths(state.root_paths)
    return {"status": "ok", "root_paths": state.root_paths}

@feature_unit(status="done")
@app.get("/add-root-input")
def add_root_input():
    return HTMLResponse('<mdui-text-field label="Root Path" name="root_paths"/>')