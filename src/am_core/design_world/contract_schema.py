from click import option


CONTRACT_SCHEMA = {
    "StateMachine": {
        "required": {
            "purpose": "string",
            "init": "List[string]", # 喔，所以這是 key names ["a","b",...] ， 因為感覺應是 {"a":Any, "b":Any, ...}
            "exposure": "List[string]",
            "scratch": "List[string]",
            "events": "List[string]",
            "refs": "List[string]"
        },
        "optional": {
            "notes": "string"
        }
    },

    "Orchestrator": {
        "required": {
            "purpose": "string",
            "init": "List[string]",
            "exposure": "List[string]",
            "scratch": "List[string]",
            "events": "List[string]",
            "refs": "List[string]"
        },
        "optional": {
            "notes": "string"
        }
    },

    "StateDeclare": {
        "required": {
            "name": "string",
            "target": "string",          # module.class, 有這個的話，還需要 registery 嗎？
            "kind": "string"            # "state" | "orchestrator", 既然有 class，還需要 kind 嗎？因為她會自己推論出來吧？
        },
        "optional": {
            "switch": "dict", # 直接 { "ok == True": "NextStep","ok == False": "ErrorState"} 嗎？
            "retry": "dict", # 改 number 嗎？
            "timeout": "dict", # 改 number 嗎？
            "notes": "string"
        }
    },
    "FeatureRef": {     # Q: 為何不直接就是 `target` 字串？
        "required": {
            "feature": "string",              # feature name
            "target": "string"                # module.class.method
        },
        "optional": {
            "kind": "string",                 # "method" | "state" | "orchestrator"
            "version": "string"
        }
    },

    "Feature": {
        "required": {
            "feature": "string",
            "status": "string"
        },
        "optional": {
            "depends_on": "List[FeatureRef]",
            "future": "List[FeatureRef]",
            "notes": "string"
        }
    },

    "Playbook": {
        "required": {
            "initial": "string",
            "states": "List[StateDeclare]",
            "registry": "Dict[string, Class]"  # 這個會不會不需要了？
        },
        "optional": {}
    }
}