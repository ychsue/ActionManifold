<meta name="htmx-config" content='{"selfRequestsOnly":false}'>
<script src="javascripts/config.js"></script>
# 🧭 ActionManifold Analysis Cockpit

## Root Paths

<form
  hx-post="am://config/root_paths"
  hx-target="#root-status"
  hx-swap="innerHTML"
>
  <div id="root-path-list">
    <!-- <input name="root_paths" placeholder="./src/features" /> -->
    <mdui-text-field label="Root Path" name="root_paths" placeholder="./src/xxx"/>
  </div>

  <mdui-button-icon icon="add"
        type="button"
        hx-get="am://add-root-input"
        hx-target="#root-path-list"
        hx-swap="beforeend"
  ></mdui-button-icon>

  <mdui-button type="submit">Set Root Paths</mdui-button>
</form>

<form
  hx-post="am://generate-md"
  hx-target="#root-status"
  hx-swap="innerHTML"
>
  <div style='display: flex; flex-wrap: wrap; width: 100%; gap: 10px;'>
    <mdui-text-field style='flex: 1 1 auto; min-width: 150px; width:12%;' name="cmd" label="command" value="roadmap"></mdui-text-field>
    <mdui-text-field style='flex: 1 1 auto; min-width: 150px; width:12%;' name="output_path" label="output_path" value=""></mdui-text-field>
    <mdui-text-field style='flex: 1 1 auto; min-width: 150px; width:12%;' name="start" label="start" value="kickoff"></mdui-text-field>
    <mdui-text-field style='flex: 1 1 auto; min-width: 150px; width:12%;' name="kickoff" label="kickoff" value="kickoff"></mdui-text-field>
  </div>
  <mdui-button type="submit">Roadmap</mdui-button>
</form>

<div id="root-status"></div>

歡迎來到 ActionManifold 的語義儀錶板。  
這裡是整個 meta‑engine 的「駕駛艙」，你可以在這裡：

- 檢視所有 FeatureUnits
- 查看 dependency graph
- 查詢某個 feature 的依賴
- 執行 feature（design‑time）
- 觀察輸出（未來可加入 runtime）

所有操作都會在本頁面完成，不會跳轉到其他頁面。

---

## 🚀 Commands

以下按鈕會透過 Zensical plugin 呼叫 am‑server 的 API，並將結果顯示在下方的 `<am-output />` 區塊。

### 🔍 Describe all FeatureUnits
[Describe](am://describe)

### 🕸 Dependency Graph
[Graph](am://graph)

### 📦 Dependencies of a FeatureUnit
請輸入 FeatureUnit

<!-- <script>
    document.body.addEventListener('htmx:beforeRequest', function (evt) { 
        console.log(`正在請求網址:${evt.detail.pathInfo.requestPath}`)
    });
</script> -->