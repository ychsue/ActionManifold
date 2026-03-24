import json
import os
import tempfile
import subprocess
from typing import Any, Dict, Optional


def edit_json_in_editor(initial: Dict[str, Any]) -> Dict[str, Any]:
    """
    Open user's default editor (EDITOR or VISUAL) with initial JSON content.
    User edits the JSON and saves.
    Return the parsed JSON dict.
    """

    # 1. 轉成漂亮的 JSON
    text = json.dumps(initial, indent=2)

    # 2. 建立暫存檔
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name
        tmp.write(text)
        tmp.flush()

    # tmp_path = "C:\\Temp\\nlog-user-info-2025-07-08.log"
    
    # 3. 找到使用者的預設編輯器
    editor = _resolve_editor()

    print(f"[interactive] Opening editor: {editor} {tmp_path}")

    # 4. 開啟編輯器
    subprocess.call(f"{editor} {tmp_path}", shell=True)

    # 5. 讀取使用者修改後的內容
    with open(tmp_path, "r") as f:
        edited = f.read()

    # 6. 刪除暫存檔
    os.unlink(tmp_path)

    # 7. 如果沒有修改，直接回傳原本的
    if edited.strip() == text.strip():
        return initial

    # 8. parse JSON
    try:
        return json.loads(edited)
    except Exception as e:
        raise ValueError(f"Invalid JSON from editor: {e}")
    
def read_json_from_stdin() -> Optional[Dict[str, Any]]:
    print("Please input JSON patch (end with an empty line):")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    text = "\n".join(lines)
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Invalid JSON: {e}")

def _resolve_editor():
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")

    if editor:
        return editor

    # Windows fallback
    if os.name == "nt":
        # VSCode 安裝後會在 PATH 放 code.cmd（但不一定在 Python PATH）
        possible = [
            r"C:\Program Files\Microsoft VS Code\bin\code.cmd",
            r"C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd",
            r"C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd".format(os.getlogin()),
        ]
        for p in possible:
            if os.path.exists(p):
                return f"\"{p}\" --wait"

        # fallback to notepad
        return "notepad"

    # Linux / macOS fallback
    return "vim"