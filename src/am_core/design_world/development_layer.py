# am_core/development_layer.py

import inspect
from .contract_schema import CONTRACT_SCHEMA

class DevelopmentLayer:
    def __init__(self, registry):
        self.registry = registry

    def extract_feature(self, method):
        doc = inspect.getdoc(method) or ""
        if "feature:" not in doc:
            return None

        result = {}
        for line in doc.split("\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if key in ("feature", "status", "notes"):
                result[key] = value
            elif key in ("depends_on", "future"):
                result[key] = [v.strip() for v in value.split(",")]

        return result

    def build_dev_items(self):
        items = []

        for name, cls in self.registry.items():
            for attr in dir(cls):
                if attr.startswith("_"):
                    continue

                method = getattr(cls, attr)
                if not inspect.isfunction(method) and not inspect.ismethod(method):
                    continue

                feature = self.extract_feature(method)
                if feature:
                    feature["id"] = f"{name}.{attr}"
                    items.append(feature)

        return items