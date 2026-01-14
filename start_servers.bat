@echo off
REM start_servers.bat - 同時啟動 Zensical 和 am_server

REM 設定 am_server URL (可以根據需要修改)
set AM_SERVER_URL=http://localhost:7000

REM 生成 config.js 文件，讓前端 JS 讀取
echo var am_server_url = "%AM_SERVER_URL%"; > docs\javascripts\config.js

echo 啟動 Zensical...
start "Zensical" cmd /c "zensical serve"

echo 啟動 am_server...
start "am_server" cmd /c "uvicorn src.am_server.main:app --reload --port 7000"

echo 伺服器已啟動。按任意鍵退出...
pause