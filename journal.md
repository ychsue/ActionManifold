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
