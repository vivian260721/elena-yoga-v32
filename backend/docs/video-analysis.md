# 影片分析

`POST /api/predict-video` 接收 `multipart/form-data` 的 `file` 欄位。

## 限制

- MP4、MOV、WebM。
- 最大 50 MiB、60 秒、3840×2160 像素總量。
- 每秒取樣 2 張，最多 120 張。
- 單人影片；不分析音訊，也不產生完整標記影片。

每個取樣影格會經過 MediaPipe、LightGBM、角度比較、骨架繪製與愛心計算。文字回饋最短每 2 秒更新一次；若排定影格無法分析，延至下一個可分析影格。

## 回傳欄位

| 欄位 | 用途 |
| --- | --- |
| `sample_fps` | 取樣率，目前 2 |
| `feedback_interval_seconds` | 回饋間隔，目前 2 秒 |
| `sampled_frames` | 取樣總數 |
| `analyzed_frames` | 成功分析數 |
| `unavailable_frames` | 無法分析數 |
| `frames` | 依時間排列的影格 |

每個 `frames[]` 包含：

- `timestamp_seconds`：相對影片時間。
- `status`：`analyzed` 或 `unavailable`。
- `prediction`：成功時與照片回應相同，失敗時為 `null`。
- `reason`：無法分析原因。
- `is_feedback_frame`：前端是否應更新文字建議。

前端整合見 [NiceGUI 前端串接](frontend-integration-guide.md)。
