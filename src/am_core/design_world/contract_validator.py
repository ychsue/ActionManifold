# am_core/contract_validator.py

class ContractValidator:
    def __init__(self, schema, playbook):
        self.schema = schema
        self.playbook = playbook
        self.errors = []

    def validate(self):
        self.check_playbook()
        self.check_states()
        self.check_orchestrators()
        return self.errors

    def check_playbook(self):
        required = ["initial", "states", "registry"]
        for r in required:
            if r not in self.playbook:
                self.errors.append(f"playbook 缺少 {r}")

    def check_states(self):
        for name, desc in self.schema["states"].items():
            for r in ("purpose", "inputs", "outputs"):
                if r not in desc:
                    self.errors.append(f"State {name} 缺少 {r}")

    def check_orchestrators(self):
        for name, desc in self.schema["orchestrators"].items():
            if "purpose" not in desc:
                self.errors.append(f"Orchestrator {name} 缺少 purpose")