# Yoga Pose Analysis Backend

FastAPI 後端，支援照片與短片的單人瑜伽姿勢分析。

處理流程：MediaPipe 取得 33 個 Landmark → LightGBM 分類五種姿勢 → 八項關節角度比較 → 固定 JSON 回饋與五級數字評分。

Default classifier: `Model/anglediff_lightgbm.joblib`. The loader takes 23 landmark xyz coordinates and eight joint angles computed from XYZ vectors (not XY projections), then appends `knee_angle_diff_deg = abs(left_knee_angle_deg - right_knee_angle_deg)` for 78 model inputs. Override the model with `LIGHTGBM_MODEL_PATH` if needed. Restart the backend after changing models.

## 快速啟動

需要 Windows 64 位元與 Python 3.11。
後端位於 `backend/`，前端位於 `frontend/`，兩者透過 HTTP API 串接，可分開部署。
後端指令先從專案根目錄切換至 `backend/`；前端另開終端機，從專案根目錄執行。

```powershell
cd backend
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/download_pose_model.py
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

- API 文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

另開終端機，在專案根目錄啟動靜態前端：

```powershell
python -m http.server 8080 --bind 127.0.0.1 --directory frontend/web
```

開啟 http://localhost:8080。原 `/preview` 已移至此獨立前端，後端不再提供介面頁面。
前端 API 位址設定於 `frontend/web/config.js`；後端允許來源設定於 `backend/.env` 的 `CORS_ORIGINS`。
NiceGUI 介面的獨立環境與啟動方式見 [前端說明](../frontend/README.md)。

## API

| API | 輸入 | 限制 |
| --- | --- | --- |
| `POST /api/predict` | `multipart/form-data` 的 `file` | JPEG／PNG／WebP，最多 10 MiB |
| `POST /api/predict-video` | `multipart/form-data` 的 `file` | MP4／MOV／WebM，最多 50 MiB、60 秒 |

影片每秒取樣 2 張；骨架與評分逐影格更新，文字回饋最短每 2 秒更新一次。

主要回傳欄位：

- `pose`：姿勢名稱。
- `comparison`：八項角度與是否符合標準。
- `rating`：依正確角度數量換算 0～5 顆蓮花（支援半顆），下犬式計單側 4 個角度，其他姿勢計 8 個角度。
- `feedback`、`suggestions`：固定句庫回饋。
- `original_image`、`skeleton_image`：Base64 data URL。
- 影片另有 `frames` 與 `is_feedback_frame`。

不需要 API key、token 或文字生成模型。

## 文件

- [快速開始](QUICK_START.md)
- [NiceGUI 前端串接](docs/frontend-integration-guide.md)
- [角度判定](docs/angle-standard.md)
- [影片分析](docs/video-analysis.md)
- [固定回饋](docs/json-feedback.md)
- [愛心評分](docs/heart-rating.md)
- [圖片與骨架](docs/prediction-images.md)
- [CSV 欄位](docs/reference-column-mapping.md)

## 測試

以下指令在 `backend/` 目錄執行。

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

LightGBM 的 `confidence` 只代表姿勢分類信心，不是動作正確率。標準判定請使用 `comparison.is_standard`，分數請使用 `rating.score`。



## Runtime separation

The frontend sends uploaded media to `/api/predict` or `/api/predict-video`. Only the backend runs MediaPipe, the 78-feature anglediff LightGBM classifier, angle comparison, rating, and feedback selection. Connection and inference errors do not produce substitute predictions. Mock predictions are confined to tests. Older model artifacts are retained for reference but are not loaded by the application.

Landmark extraction for both photos and videos uses MediaPipe Full (`Model/pose_landmarker_full.task`). Classification uses `anglediff_lightgbm.joblib` with XYZ joint angles.
