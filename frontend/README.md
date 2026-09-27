# 前端

前端只透過 HTTP API 呼叫後端，不匯入後端 Python 程式、模型或資料。
以下兩個介面擇一啟動；指令皆從專案根目錄執行。

## 網頁介面

不需要安裝後端套件。使用 Python 標準庫提供靜態檔案：

```powershell
python -m http.server 8080 --bind 127.0.0.1 --directory frontend/web
```

開啟 http://localhost:8080。照片、影片、骨架、評分與時間軸功能沿用原預覽頁。
`web/` 可以獨立部署至靜態網站服務。

在 [web/config.js](web/config.js) 設定 `API_BASE_URL`，預設為 `http://localhost:8000`。
網址必須是使用者瀏覽器能連線的後端位置，不含 `/api`。
後端 `.env` 的 `CORS_ORIGINS` 必須包含前端來源（通訊協定、主機與連接埠），多個來源以逗號分隔；修改後重啟後端。
若前端使用 HTTPS，後端網址也應使用 HTTPS。

## NiceGUI 介面

使用獨立虛擬環境，無須安裝後端模型套件：

```powershell
python -m venv frontend/.venv
frontend/.venv/Scripts/python.exe -m pip install -r frontend/requirements.txt
$env:YOGA_API_BASE_URL="http://localhost:8000"
frontend/.venv/Scripts/python.exe frontend/main.py
```

開啟 http://localhost:8080。NiceGUI 與靜態網頁預設使用相同連接埠，請擇一執行。
`YOGA_API_BASE_URL` 優先於舊名稱 `BACKEND_API_URL`；未設定時使用 `http://localhost:8000`。請在啟動終端機設定環境變數，前端不會自動載入 `.env`。
`YOGA_API_BASE_URL` 是 NiceGUI 伺服器可連線的後端位置。
部署到不同容器時，使用後端服務名稱；瀏覽器不直接使用這個網址。

API 契約與介面串接說明見 [前端串接](../backend/docs/frontend-integration-guide.md)。

主介面首頁為 `/`，分析頁為 `/analyze`。支援上傳、拍照與錄影；影片分析後可拖曳時間軸查看各影格，文字建議依 `is_feedback_frame` 更新，無法分析的影格會顯示原因。

`nicegui/main_n.py` 保留為簡易串接範例，與主介面及靜態頁使用相同連接埠，請擇一啟動。

前端回歸測試（從專案根目錄）：

```powershell
frontend/.venv/Scripts/python.exe -m unittest discover -s frontend/tests -v
```
