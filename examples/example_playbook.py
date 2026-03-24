from am_core.state_machine import StateMachine

class StartStateClass(StateMachine):
    async def _run(self, wrapped_metadata):
        # Implementation of StartState
        pass

class NextStateClass(StateMachine):
    async def _run(self, wrapped_metadata):
        # Implementation of NextState
        pass

example_playbook = {
  "initial": "StartState",
  "final": ["Success", "Error"],

  "states": [
    {
      "name": "StartState",
      "to": "NextState",
    },
    {
      "name": "NextState",
      "timeout": 30,
      "retry_times": 3,
      "switch": {
        "ok": "Success",
        "fail": "Error",
        "timeout": "Error",
        "retry": "StartState"
      }
    }
  ],

  "registry": {
    "StartState": StartStateClass,
    "NextState": NextStateClass
  }
}
