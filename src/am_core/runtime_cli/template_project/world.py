from am_core.world import World
from am_core.playbook import Playbook
import yaml
from pathlib import Path

playbook = Playbook.load_from_file("playbook.yaml")
world = World(playbook)