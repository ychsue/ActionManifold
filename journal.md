# [2026-02-15] 準備自己寫一下想像中的 Orchestrator

# [2026-02-10] 繼續準備，多了一個 ctx["rehearsal"] 的 class
1. [orchestrator.py](src\am_core\orchestrator.py) 將 event_log 與 emit 分開來存。

# [2026-02-09] 做了點小修改，預備開始實作 resume

# [2026-02-06] 整個 playbook 的 schema 修改
1. 現在長
``` py
PlaybookDict {
    "initial": str,
    "final": [str],
    "states": [
        {
            "name": str,
            "to": Optional[str],
            "switch": Optional[dict[str,str]],
            "timeout": Optional[number],
            "retry_times": Optional[number],

            # constructor info
            "class": Optional[str],        # Python class path
            "subflow": Optional[str|dict], # nested Playbook
            "builtin": Optional[str],      # "Success", "Error", ...
            "workdir": Optional[str],      # reserved for WORLD
        }
    ],
    "registry": {
        stateName: {
            "class": Optional[type],       # Python class
            "subflow": Optional[Playbook], # nested Playbook
            "workdir": Optional[str],
        } | StateMachine
    }
}
```
2. 其他的就搭配他修改


# [2026-02-04] 已經有新的 orch, SM 了
不過，
1. orchestrator 是使用各別的class 繼承 Orchestrator，若沒有提供，則是直接使用 Orchestrator
2. 我在 [playbook.py](src\am_core\playbook.py) 多加了
   ``` py
    entry = self.registry[state]
    playbook = entry.get("playbook")
    playbook = Playbook(playbook, base_path=self.base_path) if isinstance(playbook, dict) else playbook
   ```
   不曉得這樣能否也接受使用者直接將playbook 寫在 register 裡面，而形成巢狀？

# [2026-02-02] runtime 設計中，以Test First 來設計，謝謝Copilot

1. playbook 有一個物件來管理：  [test_playbook_wrapper.py](tests\runtime\test_playbook_wrapper.py) -> [playbook.py](src\am_core\playbook.py)
2. run_watcher 來包裝run的結果，不過，他不包住 run [test_run_watcher.py](tests\runtime\test_run_watcher.py) -> [run_watcher](src\am_core\run_watcher.py)
3. decision_block 用來切換 state [test_decision_block.py](tests\runtime\test_decision_block.py) -> [decision_block.py](src\am_core\decision_block.py)

# [2026-01-28] 我得先回來 runtime 的設計

1. 參考 [DISCUSSION_dev_run.md](discussions\DISCUSSION_dev_run.md) 的最後一個討論，先完成 runtime
2. [DISCUSSION_BU.md](discussions/DISCUSSION_BU.md) line 10080 以後的部分得完成

# [2026-01-14] v0.1.1 準備上 Github
1. [am_server](src\am_server\main.py) 由於接收的是 htmx 的 DataForm，所以，使用 
  ``` py
  Annotated[str, Form()]
  ```
  將想要的型別(如 `str`) 包在裏頭，這樣才能取得前端的API呼叫。

1. [start_servers.bat](start_servers.bat) 呼叫此檔，可以同時開啟 Zensical 與 am_server(很陽春，還早)，方便開發。

# [2026-01-11] 已經請Grok 簡單寫了，正要測

# [2026-01-11] Gantt 圖需要的時間宣告法Copilot 提出，然後Grok幫忙完整
- [ ] 下一步，使 timeline, gantt 與 graph 可以輸出 mermaid 格式

# [2026-01-10] 將zensical 當前端，am_server 當後端
- zensical:
  - [zensical.toml](zensical.toml) 裡面使用了 mdui 2 與 htmx
- am_server:
  - [main.py](src\am_server\main.py)
- [x] 我想要使用 gantt，所以，顯然我得讓 scheduled 與 due 兩個能夠套用別的 unit 的時間為相對時間

# [2026-01-08] 準備加上 pytest ， Grok 幫忙加上了。

# [2026-01-06] 準備在 feature 的 graph 加上 mainline 的分析 

# [2026-01-03] 想做的
## [ ] 1️⃣ Description Layer（規格層）  
→ 產生 spec.md  
→ 這是所有層級的基礎

## [ ] 2️⃣ Development Layer（開發層）  
→ 產生 dev.md  
→ TODO / 進度 / 完成度

## [ ] 3️⃣ Execution Layer（執行層）  
→ run_watcher / decision_block / metadata

## [ ] 4️⃣ Analysis Layer（分析層）  
→ performance / progress / replay insights

## [ ] 5️⃣ Meta‑AM（AM 管理 AM）  
→ 讓 AM 自己 orchestrate 自己的開發

# [2026-01-02] 初步可用的 ActionManifold 的原型大致完成，謝謝 Copilot 的幫忙
