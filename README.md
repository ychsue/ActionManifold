# ActionManifold
任務(Action)在事件與時間中所能展開的所有可能路徑的流形

---
首先，這個部分是 [超導般的社會](https://ychsue.github.io/superconductorlike_society/) 裡需要的一部份。

主要是因為若要能夠讓 AI Agent 能夠handle 人們的活動，然後根據活動數據持續優化或者擴充，甚至能夠 replay 與 resume 的話，那就需要有一些定好的協定。

之所以稱為 ActionManifold，是因為這是以活動為主，其實很像 n8n 或 nodered 等，但是，我希望能夠同時能處理 design time 與 runtime 的控制。

## Development Time
### 如何設定
這個部分，乃是透過 [@feature_unit(.....)](./src/am_core/feature/feature_unit.py) 來設定，由 [core_mainline.py](./am_meta/core_mainline.py) 可以看到怎麼設定他，而Gantt 圖的時間算法則設計於 [resolve_time.py](./src/am_core/feature/resolve_time.py)。

雖然我把專案規畫寫在 [core_mainline.py](./am_meta/core_mainline.py) 裡面，但是，您可以把 `@feature_unit` 加在任何的 function 與 class 上面。
這樣，您可以將專案時程管理套用到專案內部裡也沒有問題。

### command line 分析
可透過 `am dump-all-dev-mds` 來輸出 markdown 檔案們來看，他會放到您的 `docs` 目錄裡面。
還有其他的命令，您可以下 `am --help` 來查看

### 使用 Zensical 視覺化 Gantt 、 Timeline 等
請安裝完 `uvicorn` 與 `zensical` 後，下載 [start_servers.bat](start_servers.bat)與在您的專案的 `docs` 目錄放置 [docs/javascripts/am_protocol_handler.js](./docs/javascripts/am_protocol_handler.js) 與 [index.md](./docs/index.md)後，執行
``` ps1
./start_server.bat
```
這樣就能看到您在 [上個章節](#command-line-分析) 執行而產生的 Markdown 檔案們。

### 開發進程
* 目前 v0.1.1 [2026-01-13] 目前能動，但不完美，還有許多可以改進，不過，更重要的是 runtime 的部分，目前先這樣，先把 runtime 做得更完整。
* [ ]  **TODO TODO TODO** 我需要一個 Scheduler，所以，雖然目前 [core_mainline.py](./am_meta/core_mainline.py) 的執行單元是以函數的形式存在，未來可以以 StateMachine 代替，然後有 Orchestrator 可以統一執行，然後我可能要再設計一個 `run_dev` 來跑 scheduler，這樣，他就可以幫我控管時間與進程紀錄了。

## Runtime
當我在寫RPA的程式時，寫好一個能動的版本後，常常需要一直加補丁上去，原因無他，因為會有許多的例外發生。
這很正常，因為除了 Browser 可以是我們的 Project 的一部分之外，其實，仔細想想，無論是網頁內容、ERP、Windows UI 與其他軟體等，都是我們等他們對我們的RPA的操作有所反應，也就是 event-driven，而且，他們的 events 很可能五花八門，所以，穩健的做法就得
1. 監聽回覆與突發事件
2. 對事件能即時做出正確的回應
3. 當客戶需求改變，甚至可以不用修改程式主體，就可以直接改變流程

然後，出問題時，能否簡單的 replay 所經過的步驟(不用真的執行，只要修改 contexts)，然後，可以在想要的步驟開始 resume 執行，這樣應該就能監看發生甚麼事了，因此，也就可以只針對有問題的 StateMachine做優化。所以，還需要
1. 可 Replay
2. 可 Resume
3. 可擴充

- [ ] 未來，甚至可以像 SCXML 那樣能監看當前跑到哪個步驟等，之所以不使用 SCXML，是因為 transitions 不是重點，重點在 actions，而串接這些 transitions 的部分，則在 Orchestrator 宣告，這個宣告未來很可能可以移到 .json 或 .toml 檔上面，這樣，甚至可以在執行期間，直接動態更改 transitions。

所以，元件主體為
1. [Orchestrator](./src/am_core/orchestrator.py) 
   1. [ ] 未來應該還會增加 `ParallelOrch` 好讓他們有可能 async 來同時跑好幾個 SM or Orch
2. [StateMachine(SM) & WorldRunner](./src/am_core/state_machine.py)
   1. [ ] `WorldRunner` 其實原本是最上層的 `Orchestrator`，然而，就像化學分子一樣，若 SM 看成是原子，那麼，Orchestrator 則是宣告他們怎麼鍵結在一起。而當好幾個分子互相作用時，當然我們也可以看做就是一堆的原子雜在一起，若分子的各自特徵在相互作用中，仍然維持的話，把它看作一個類原子可能比較好。所以， `replay` 與 `resume` 的語法是寫在 `WorldRunner` 上，然後，對外而言，他看起來會就像一個SM或說原子一樣。所以，把它放在 [state_machine.py](./src/am_core/state_machine.py)
3. [StateCtx, OrchCtx, WorldCtx](./src/am_core/context.py)
   1. 原則上，WorldRunner,Orch, 與 SM ，這三個是runtime行動的藍圖，是個網狀。
   2. Contexts 則是上述的 `runtime行動藍圖` 在runtime時資料共享網。
4. [CtxBus](./src/am_core/context.py) 是想說提供一個跨全域可訂閱的Context，目前還沒有使用，但您可以試看看。

如何串接可以參照 [example.py](examples\example.py)，抱歉，由於還在演化當中，例子就先這樣。