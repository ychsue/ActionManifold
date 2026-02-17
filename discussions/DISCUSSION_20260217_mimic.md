# 旨在讓 resume 能動

## [2026-02-17] ychsue 提供 Copilot 目前不成熟的 orchestrator.py

### Copilot's Answer 01

你這版其實已經把「問題講給自己聽」了——你在檔案裡做的拆分是對的，只是有幾個關鍵地方現在是「半步到位」，我幫你把它們點出來，順便整理成幾個可以直接改的方向。

我先用你現在的語意來講，而不是丟一堆新設計。

---

#### 1. 你現在其實有「兩套 pointer 系統」，而且是錯開的

你現在有：

- `rehearsal.pointer`：給 `event_log` / `event_log_resume` 用  
- `self.replay_events` + `self.replay_pointer`：給「本層」用（但目前只用在 `get_current_id`）

問題是：

- `before_ini_child` / `after_decision` 在用的是 `rehearsal.pointer` + `event_log_resume`  
- `get_current_id` 在用的是 `self.replay_pointer` + `self.replay_events`  
- `run()` 裡的 resume 判斷卻是拿 `self.get_current_id(self.replay_pointer+1)` 去對 `rehearsal.unpaired_event_ids`  

也就是說：**replay/resume 的判斷是看 A 這組 pointer，實際 restore 的 event 卻是從 B 那組 list 拿的**——這一定會出錯，而且 nested orch 時會更亂。

> 建議：  
> 先選一個「真實 pointer」，不要兩套。  
> 要嘛全部用 `rehearsal.event_log_resume + rehearsal.pointer`，  
> 要嘛全部用 `self.replay_events + self.replay_pointer`。  
> 以你現在的設計，我會建議：  
> 👉「本層 replay/resume 一律用 `self.replay_events` + `self.replay_pointer`，`Rehearsal` 只存全域 event_log，不再存 pointer。」

---

#### 2. `before_ini_child` / `after_decision` 的 restore 邏輯現在是「空殼」

你自己也有寫 TODO：

```python
## TODO 感覺應該更新metadata & child_ctx，因為他們要被 bypass 掉
```

現在的行為是：

- `restore_event=True` 時：
  - `before_ini_child`：`rehearsal.pointer += 1`，從 `event_log_resume` 拿 event_id，**但沒有更新任何 ctx / metadata**  
  - `after_decision`：`rehearsal.pointer += 1`，從 `event_log_resume` 拿 event，**也沒有更新 ctx / metadata**

這代表：

- replay/resume 模式下，**你完全沒有 apply 過去的 ctx_delta / metadata**  
- 也就是說，現在的 replay/resume 只是「跳過執行」，但沒有「重建語意狀態」  

> 建議：  
> 在 `after_decision(restore_event=True)` 裡，應該：  
> - 從 `event_log_resume` 拿到對應的 `after_decision` event  
> - `self.ctx.apply_delta(event["ctx_delta"])`  
> - `self.metadata = event["metadata"]`  
> - 不 emit、不 append event_log  
> - 不跑 run_watcher / decision_block（你已經在 run 裡跳過了，這點是對的）

---

#### 3. resume 的核心判斷現在是「繞一圈」而且容易錯

你現在的 resume 判斷：

```python
if rehearsal.mode == "resume":
    if rehearsal.exec_status == "replay":
        if self.get_current_id(self.replay_pointer+1) not in rehearsal.unpaired_event_ids:
            restore_event = True
            pass_execution = True
        else:
            restore_event = False
            pass_execution = False
    elif rehearsal.exec_status == "running":
        restore_event = False
        pass_execution = False
    elif rehearsal.exec_status == "stopped":
        restore_event = True
        pass_execution = True
```

問題有幾個：

1. `exec_status` 的狀態機現在沒有被任何地方「明確推進」，它永遠是 `"running"` 或你手動改。  
2. `get_current_id(self.replay_pointer+1)` 用的是 `self.replay_events`，但 `unpaired_event_ids` 是從 `event_log_resume` 算出來的——兩個 list 不一定對齊。  
3. resume 的語意其實可以更簡單：  
   - 在 `prepare_resume` 時就把「要 mimic 的 event 範圍」切好  
   - run 裡只要：  
     - 如果這個 state 有對應的 `before_ini_child + after_decision` → mimic  
     - 否則 → 正常執行  

你現在是用「有沒有成對」來判斷「要不要執行」，這個方向是對的，但實作上繞太多層，而且 pointer 不一致。

> 建議：  
> - `prepare_resume` 做兩件事就好：  
>   1. 把「要 replay 的那一段 event_log」切成 `event_log_resume`  
>   2. 算出「哪些 id 是 unpaired（沒有 after_decision）」  
> - run 裡的 resume 判斷可以簡化成：  
>   - 如果 current_state 對應的 event_id 在 `unpaired_event_ids` → 這個 state 要「重新執行」  
>   - 否則 → 這個 state 可以 mimic（restore_event=True, pass_execution=True）

---

#### 4. `level` 現在幾乎沒真的用到

你現在有：

```python
if rehearsal.mode == "replay":
    if rehearsal.level in ["orch"] or (rehearsal.level == "state" and self.playbook.is_state_machine(current_state)):
        pass_execution = True
    else:
        pass_execution = False
```

問題是：

- `restore_event` 在 replay 模式下永遠是 True（因為一開始就 `restore_event = True if mode in ["replay", "resume"]`）  
- `level` 只影響 `pass_execution`，但不影響「從哪裡 restore event」、「restore 到什麼程度」  
- 也就是說：**現在的 level 只是「要不要執行 child.run」的開關，還沒有真的做到「orch/state/sm 粒度」**

> 建議：  
> 先暫時不要硬撐 level，把 replay 先做到「這一層 orch 的 state_exit mimic 正確」，  
> 等這個穩了，再來拆：  
> - level="orch" → 只看 before/after_decision，不管 ctx_delta  
> - level="state" → apply ctx_delta / metadata  
> - level="sm" → orchestrator 只 mimic 到 state_exit，state 裡的 replay 交給 SM 自己  

---

#### 5. 你做對的一件大事：把 run 拆成 before/ini_child/exec_child/after_decision

這個拆法超好，因為：

- replay/resume 只要在這四個階段決定「要不要真的做」  
- 你已經把 run_watcher / decision_block / emit / event_log append 都集中在 `exec_child` + `after_decision` 裡  
- 這讓 replay/resume 可以「只改行為，不改結構」

你現在的骨架是對的，只是 replay/resume 的判斷還在「半空中」。

---

#### 6. 如果要「先把 replay 做到穩」，我會建議你這樣收斂

先不管 resume_from、多層 exec_status、多種 level，先把最小 replay 語意做對：

**目標：**  
給一段完整的 `event_log`，  
`mode="replay"` 時，  
orchestrator 跑完一輪後：  
- 不執行任何 child.run  
- 不跑 run_watcher / decision_block  
- 不 emit 新 event  
- 只 apply ctx_delta / metadata  
- current_state / metadata / ctx 最後狀態要跟原本 run 完一樣  

要做到這個，其實只要：

1. `prepare_resume` 不動（或簡化成 `event_log_resume = event_log.copy()`）  
2. run 裡：  
   - `restore_event=True`  
   - `pass_execution=True`  
3. `before_ini_child(restore_event=True)`：  
   - 從 `event_log_resume` 找對應的 `before_ini_child` event（用 pointer）  
   - 只拿 id，不 emit、不 append  
4. `after_decision(restore_event=True)`：  
   - 從 `event_log_resume` 找對應的 `after_decision` event（用 pointer）  
   - `self.ctx.apply_delta(event["ctx_delta"])`  
   - `self.metadata = event["metadata"]`  
   - 不 emit、不 append  

這樣你就有一個「純 mimic」的 replay，  
之後再在這個基礎上加 resume / level / nested。

---

如果你願意，我可以幫你做一件很具體的事：

> 直接在你這版 orchestrator.py 上，  
> 寫一個「只處理 mode='replay'、不管 resume/level 的最小修正版」，  
> 讓你可以先有一個「replay 一定正確」的基準點，  
> 再往 resume / level 疊上去。

你如果覺得這樣比較好走，就跟我說一聲：  
「好，我們先把最小 replay 寫到穩。」

