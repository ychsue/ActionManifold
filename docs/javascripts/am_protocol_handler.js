// docs/javascripts/am_protocol_handler.js
// 攔截 htmx 請求，將 am:// 協議轉換為代理路徑改成am_server 的 URL
am_server_url = "http://localhost:7000";
document.body.addEventListener("htmx:configRequest", function (e) {
  const url = e.detail.path;

  if (url.startsWith("am://")) {
    const command = url.replace("am://", am_server_url + "/");
    const newUrl = command;
    console.log("htmx intercepted AM URL:", url, "->", newUrl);
    // 改寫 htmx 的 request URL
    e.detail.path = newUrl;
  }
});

// 攔截所有 click（處理 a、button、任何 clickable）
document.addEventListener("click", function (e) {
    console.log("Click event:", e);
  const el = e.target.closest("[href], [data-href]");
  if (!el) return;

  const url = el.getAttribute("href") || el.getAttribute("data-href");
  console.log("Clicked URL:", url);
  if (!url || !url.startsWith("am://")) return;

  e.preventDefault();
  handleAM(url);
});

// 攔截所有 form submit
document.addEventListener("submit", function (e) {
  const form = e.target;
  const action = form.getAttribute("action");
  if (!action || !action.startsWith("am://")) return;

  e.preventDefault();
  handleAM(action, new FormData(form));
});

// 通用處理器
function handleAM(amUrl, formData) {
  const command = amUrl.replace("am://", am_server_url + "/");
  console.log("Handling AM command:", command);

  const newUrl = command;

  if (formData) {
    fetch(newUrl, { method: "POST", body: formData });
  } else {
    window.location.href = newUrl;
  }
}
