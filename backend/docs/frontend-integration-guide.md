# NiceGUI 前端串接

完整介面：[main.py](../../frontend/main.py)。前端不需要 API key、Landmark 計算或固定句庫。
前端程式與依賴已獨立放在 `frontend/`，不匯入後端模組。
另有可獨立部署的 [靜態網頁介面](../../frontend/README.md)。

## 啟動

以下指令從專案根目錄執行；首頁為 `/`，分析頁為 `/analyze`。

```powershell
python -m venv frontend/.venv
frontend/.venv/Scripts/python.exe -m pip install -r frontend/requirements.txt
$env:YOGA_API_BASE_URL="http://localhost:8000"
frontend/.venv/Scripts/python.exe frontend/main.py
```

## 上傳檔案

NiceGUI 3 使用 `await event.file.read()`：

```python
import httpx
from nicegui import events, ui

API_BASE_URL = "http://localhost:8000"


async def handle_upload(event: events.UploadEventArguments) -> None:
    content = await event.file.read()
    name = event.file.name
    content_type = event.file.content_type or "application/octet-stream"
    is_video = content_type.startswith("video/") or name.lower().endswith((".mp4", ".mov", ".webm"))
    endpoint = "/api/predict-video" if is_video else "/api/predict"

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            f"{API_BASE_URL}{endpoint}",
            files={"file": (name, content, content_type)},
        )

    data = response.json()
    if response.is_error:
        raise RuntimeError(data.get("detail", "分析失敗"))
    show_result(data, is_video)


ui.upload(
    on_upload=handle_upload,
    auto_upload=True,
    max_file_size=50 * 1024 * 1024,
).props("accept=.jpg,.jpeg,.png,.webp,.mp4,.mov,.webm")
```

API base URL 應在啟動終端機設定為 `YOGA_API_BASE_URL`，前端不會自動載入 `.env`。主介面也相容舊名稱 `BACKEND_API_URL`，但 `YOGA_API_BASE_URL` 優先。NiceGUI 和後端若分屬不同容器，使用後端服務名稱，不要使用容器內的 `localhost`。

## 顯示結果

| JSON 欄位 | NiceGUI 元件 |
| --- | --- |
| `pose` | `ui.label` |
| `comparison.overall_assessment` | `ui.label` |
| `rating` | 姿勢分類旁的數字評分與比例標籤 |
| `feedback` | 回饋標籤 |
| `suggestions` | `ui.column` 內逐項建立標籤 |
| `original_image`、`skeleton_image` | `ui.image.set_source()` |

```python
def show_rating(rating: dict | None) -> None:
    count = rating.get("score") if rating else None
    if count is None:
        score.set_text("無法評分")
        return
    score.set_text(f"{count} / {rating['max_score']} 分")
```

圖片欄位已是 Base64 data URL，可直接傳給 `set_source()`。

## 影片回饋

影片每秒取樣 2 張，但文字回饋最短每 2 秒更新一次。顯示目前影格時：

1. 先檢查 `frame["prediction"]` 是否存在。
2. 骨架、姿勢與分數可隨影格更新。
3. 只有 `frame["is_feedback_frame"]` 為 `true` 時更新文字。
4. 其他影格保留上一則文字，不要清空。

```python
latest_feedback = None
for frame in frames[:current_index + 1]:
    if frame["is_feedback_frame"] and frame["prediction"]:
        latest_feedback = frame["prediction"]
```

## 錯誤與多人使用

- `400`：檔案無效。
- `413`：檔案過大或影片過長。
- `422`：沒有檔案、人體或足夠關鍵點。
- `500`：後端錯誤。

以 `ui.notify(str(error), type="negative")` 顯示錯誤。影片請求建議 timeout 設為 180 秒。

畫面元件與 `video_frames` 應放在 `@ui.page` 函式內，不要用模組全域變數共用不同使用者的結果。

