# src/am_server/main.py

from dataclasses import dataclass
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from typing import List

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

@feature_unit(status="done")
@app.post("/config/root_paths")
def set_root_paths(root_paths: List[str] = Form(...)):
    state.root_paths = [r for r in root_paths if r.strip()]
    return {"status": "ok", "root_paths": state.root_paths}

@feature_unit(status="done")
@app.get("/add-root-input")
def add_root_input():
    return HTMLResponse('<mdui-text-field label="Root Path" name="root_paths"/>')