# Docker 打包與啟動

本設定啟動 FastAPI 後端與 NiceGUI 前端，使用 Python 3.11、Linux amd64 容器。
Windows 請先啟動 Docker Desktop，並使用 Linux containers。

## 啟動

在專案根目錄執行：

```powershell
docker compose up -d --build
docker compose ps
```

- 前端：http://localhost:8080
- 分析頁：http://localhost:8080/analyze
- 後端文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

目前本機 Python 服務也使用 8000、8080。若保留本機服務，請改用其他宿主連接埠：

```powershell
$env:BACKEND_PORT="8001"
$env:FRONTEND_PORT="8081"
docker compose up -d --build
```

此時前端為 http://localhost:8081，後端文件為 http://localhost:8001/docs。
前端容器透過 `http://backend:8000` 呼叫後端，宿主連接埠改變不影響容器間連線。
預設僅允許本機連入。相機功能請由 localhost 開啟；遠端部署需另配置 HTTPS。

## 模型與設定

- `backend/Model/anglediff_lightgbm.joblib` 必須存在，會打包進後端映像；Git 不忽略此模型。
- `backend/Model/pose_landmarker_full.task` 存在時直接打包；不存在時，建置步驟會下載官方模型。
- MediaPipe 模型可重新下載，因此 `.gitignore` 排除 `.task`；`.dockerignore` 不排除此檔案。
- 參考 CSV、正式回饋句庫與評分資料會包含在後端映像。
- 本機 `.env`、虛擬環境、快取及日誌不會打包進映像。設定請透過 Compose 的 `environment` 提供。
- 容器內停用 NiceGUI 自動重載；本機直接執行仍預設開啟重載。
- 首次建置需要網路下載基底映像、系統套件與 Python 套件。

## 維護

```powershell
# 查看紀錄
docker compose logs -f

# 修改程式後重建並更新
docker compose up -d --build

# 停止並移除容器
docker compose down
```

原始碼不掛載至容器，因此修改程式後需要重新建置。

## Git 忽略規則

根目錄 `.gitignore` 排除本機環境變數、虛擬環境、Python 快取、日誌、清理備份及下載模型。
保留 `.env.example`、Docker 設定、程式碼、正式資料與分類模型。
忽略規則不會自動取消已追蹤檔案的 Git 追蹤。
