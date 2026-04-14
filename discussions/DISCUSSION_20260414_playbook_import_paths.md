# Playbook Import Path Discussion

## [2026-04-14] Summary

這份討論整理 ActionManifold 在 Playbook `class_` 路徑解析上的設計決策，避免把相關結論混在 `DISCUSSION_20260404_UI.md` 之中。

## 背景

`template_project` 原本混用了兩種 `class_` 寫法：

- 相對路徑，例如 `.states.step1.Step1`
- 絕對路徑，例如 `project.states.step2.Step2`

這會帶來兩個問題：

1. template 複製到任意目錄後，`project.*` 並不是天然可 import 的 Python package。
2. 若直接依賴一般 `importlib.import_module("states.step1")`，不同 playbook 底下的 `states.*` 可能互相污染。

## 本次決策

### 1. 相對路徑的語義

相對 `class_` 一律解釋為：

- 以當前 `playbook.yaml` 所在目錄為基準
- 不依賴使用者手動設定 `sys.path`

範例：

```yaml
class_: .states.step1.Step1
```

表示到當前 playbook 目錄下尋找 `states/step1.py` 裡的 `Step1`。

### 2. 絕對路徑的語義

絕對 `class_` 一律解釋為標準 Python import path：

- Runtime 不替使用者改寫前綴
- Runtime 不自動替使用者補 `sys.path`
- 是否可 import，由使用者自己保證

範例：

```yaml
class_: my_shared_pkg.sms.review.ReviewSM
```

適合給跨多個 subflow 或跨專案共用的正式 Python package 元件。

### 3. 暫不支援 root alias

目前先不引入這類語法：

- `@root.states.step1.Step1`
- `root:states.step1.Step1`

理由：

- 現階段先維持規則單純
- 避免把 framework 語法與 Python import 語法混在一起
- 若未來需要，再作為第三種明確語義加入

## 已採用的技術作法

為了讓相對路徑不依賴全域 `sys.path`，目前實作採用：

1. 依 `playbook.base_path` 建立一個動態 package 名稱
2. 將該 package 放入 `sys.modules`
3. 以 `importlib.import_module()` 從這個動態 package 往下載入 `states.*`

這樣可以讓不同 playbook 各自擁有隔離的 module namespace。

## 關於 `sys.modules`

### 1. 同一個 playbook 不會重複建立 package

動態 package 名稱是由 `base_path` 推導而來，因此：

- 同一個 `base_path` 只會建立一次
- 後續會直接重用 `sys.modules` 中既有的 module entry

### 2. 這不是 GC 問題，而是 cache policy 問題

模組一旦放進 `sys.modules`，就會被 Python import system 快取。

這不是立即性的 memory leak，但若未來有一個長時間運行的中控中心，不斷載入很多不同 `world` / `playbook.base_path`，那麼 `_am_pb_*` 這類動態 package 可能持續累積。

### 3. 清理策略應留到中控中心層

本次討論的共識是：

- 目前先不在底層 import helper 自動清理 `sys.modules`
- 未來若有中控中心，再由該層統一管理 module cache policy

因為只有中控中心才知道：

- 哪些 `world` 仍在執行
- 哪些 playbook 最近仍被使用
- 哪些 module 可以安全 eviction

## 未來中控中心可做的事

若未來要做動態 module cache 管理，建議不要直接掃 `sys.modules` 硬刪，而是額外維護一份 registry，例如：

- `base_path -> package_name`
- `package_name -> last_used_at`
- `package_name -> active_world_count`
- `package_name -> loaded_submodules`

如此才能安全地做 idle eviction 或週期性清理。

## 文件與規則輸出

本次已新增對使用者的規則文件：

- `README_Playbook.md`

內容重點：

- 相對路徑：由 playbook 所在目錄解析
- 絕對路徑：遵守標準 Python import
- template project 建議全面使用相對路徑

## 小結

目前的規則分工如下：

1. 本地 flow 內部 state：使用相對 `class_`
2. 跨 subflow / 跨專案共用元件：使用標準 Python 絕對 import path
3. root alias：暫不實作，未來可再加入
4. module cache 清理：暫不在底層處理，未來由中控中心負責