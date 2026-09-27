# 快速開始

## 後端

```powershell
cd backend
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/download_pose_model.py
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

API 文件：http://localhost:8000/docs

## 網頁前端

保持後端執行，另開終端機，在專案根目錄執行：

```powershell
python -m http.server 8080 --bind 127.0.0.1 --directory frontend/web
```

開啟：http://localhost:8080

前端 API 位址：`frontend/web/config.js` 的 `API_BASE_URL`。
後端允許來源：`backend/.env` 的 `CORS_ORIGINS`，預設允許本機 8080 連接埠。
前端可獨立部署；後端不再提供 `/preview`。
如需 NiceGUI，請依 [前端說明](../frontend/README.md) 使用獨立環境啟動。

## API 測試

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/predict" -F "file=@C:/photos/yoga.jpg"
```

更多前端資訊見 [NiceGUI 前端串接](docs/frontend-integration-guide.md)。

