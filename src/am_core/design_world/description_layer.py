# am_core/description_layer.py

import inspect
from .contract_schema import CONTRACT_SCHEMA

class DescriptionLayer:
    def __init__(self, playbook):
        self.playbook = playbook

    def extract_doc(self, cls):
        doc = inspect.getdoc(cls) or ""
        result = {}

        for line in doc.split("\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if key in ("purpose", "notes"):
                result[key] = value
            elif key in ("inputs", "outputs"):
                result[key] = [v.strip() for v in value.split(",")]

        if hasattr(cls, "description"):
            result.update(cls.description)

        return result

    def extract_decisions(self):
        decisions = {}
        for st in self.playbook.get("states", []):
            name = st["name"]
            decisions[name] = {}

            for key in ("to", "switch", "retry", "timeout"):
                if key in st:
                    decisions[name][key] = st[key]

        return decisions

    def build_schema(self):
        schema = {
            "workflow": {
                "id": self.playbook.get("id", "UnknownWorkflow"),
                "initial": self.playbook.get("initial")
            },
            "states": {},
            "orchestrators": {},
            "decisions": self.extract_decisions()
        }

        registry = self.playbook.get("registry", {})

        for name, cls in registry.items():
            desc = self.extract_doc(cls)

            bases = [b.__name__ for b in cls.__bases__]
            if "StateMachine" in bases:
                schema["states"][name] = desc
            else:
                schema["orchestrators"][name] = desc

        return schema