# Playbook Class Path Rules

這份文件說明 Playbook 中 `class_` 欄位的解析規則，特別是相對路徑與絕對路徑的使用方式。

## Design Summary

ActionManifold 目前對 Playbook `class_` 採用兩層語義：

1. 相對路徑以當前 `playbook.yaml` 所在目錄為基準解析，例如 `.states.step1.Step1`。
2. 絕對路徑視為標準 Python import path，例如 `my_shared_pkg.sms.review.ReviewSM`，是否可 import 由使用者自行保證。

這個設計的目標是把 template project 內部 state 與真正可重用的 shared package 分開處理：

- 本地 flow 內部元件優先使用相對路徑，避免把專案綁死在某個固定 package 名稱。
- 跨 subflow 或跨專案共用的元件使用標準 Python 絕對路徑，維持與 Python import system 一致。

目前暫不引入 `@root` 之類的 framework root alias。若未來需要擴充，會將它視為第三種明確語義，而不是對絕對路徑做字串替換。

另外，為了讓相對路徑不依賴全域 `sys.path`，runtime 目前會依 `playbook.base_path` 建立隔離的動態 module namespace。這些 module 會交由 Python import cache 管理；若未來需要 cache eviction，預期會由更上層的中控中心或 scheduler 統一處理，而不是在底層 import helper 自動回收。

## 設計原則

1. Playbook 內的本地 state，應盡量使用相對路徑。
2. 跨多個 subflow 共用的 StateMachine，可使用標準 Python 絕對 import path。
3. Runtime 不額外發明新的 import 語法；絕對路徑即代表標準 Python import。

## `class_` 的兩種寫法

### 1. 相對路徑

範例：

```yaml
class_: .states.step1.Step1
```

語義：

- 以目前 `playbook.yaml` 所在目錄為基準解析。
- 適合 template project 內部的本地 state。
- 搬動整個 flow 目錄時，通常不需要修改 class path。

例如：

- `playbook.yaml` 位於 `C:/demo_flow/`
- `class_: .states.step1.Step1`
- 對應檔案應位於 `C:/demo_flow/states/step1.py`

若是子流程的 `playbook.yaml` 位於 `C:/demo_flow/subflows/subflow_a/`，則：

- `class_: .states.a1.A1`
- 對應檔案應位於 `C:/demo_flow/subflows/subflow_a/states/a1.py`

### 2. 絕對路徑

範例：

```yaml
class_: my_shared_pkg.sms.review.ReviewSM
```

語義：

- 這是標準 Python import path。
- Runtime 會直接依 Python import system 嘗試載入。
- ActionManifold 不會替你自動補 `sys.path` 或替換前綴。

適用情境：

- 同一個 StateMachine 需要被多個 subflow 共用。
- 共用元件已經放在正式 Python package 中。
- 或者使用者已自行確保該模組可以被 Python import。

## 使用絕對路徑時，使用者需要自行保證的事

至少滿足以下其一：

1. 該模組已安裝在目前 Python environment 中。
2. 專案啟動前已正確設定 `sys.path`。
3. 以 package 方式組織專案，且執行入口位於正確的 import context。

如果沒有滿足上述條件，Python 可能會拋出 `ModuleNotFoundError`。

## 建議的使用策略

建議優先順序如下：

1. 同一個 playbook 或 subflow 內部的 state：使用相對路徑。
2. 多個 flow 共用的正式元件：使用絕對路徑。
3. 不要把臨時專案目錄假裝成固定名稱的頂層 package，除非你真的要把它 package 化。

## 目前不支援的寫法

目前暫不支援這類 framework 自訂 root alias：

- `@root.states.step1.Step1`
- `root:states.step1.Step1`

未來如果需要，這類語法可以再加入；但目前先維持規則單純：

- 相對路徑：由 playbook 所在目錄解析
- 絕對路徑：遵守標準 Python import

## 對 template project 的建議

`template_project` 內的 `class_` 建議全部使用相對路徑，這樣 `init_project` 複製到任意目錄後都較容易運作與維護。

## 給維護者的備註

若未來要加入 root alias，建議把它當成第三種明確語義，而不是對絕對路徑做字串替換。這樣可以避免和標準 Python import path 混淆。