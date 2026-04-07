import click
import os
import shutil
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "template_project"

@click.group()
def cli():
    """AM Runtime CLI"""
    pass

def init_project(path: str):
    """
    初始化一個 AM Runtime Project
    """
    target = Path(path)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    for root, dirs, files in os.walk(TEMPLATE_DIR):
        rel = os.path.relpath(root, TEMPLATE_DIR)
        target_dir = target / rel
        target_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            shutil.copy(Path(root) / f, target_dir / f)

    
@cli.command()
@click.argument("path", default=".")
def init(path):
    """初始化一個 AM Runtime Project"""
    init_project(path)
    click.echo(f"✅ AM Runtime Project initialized at {path}")
    