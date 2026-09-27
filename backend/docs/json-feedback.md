# 固定 JSON 回饋

照片與影片一律由 `utils/json_feedback.py` 從 `data/pose_feedback_fix.json` 選取預寫句子。不需要 LLM、API key 或 token。

句庫包含五個姿勢、八項角度及四種狀態：

| 狀態 | 意義 |
| --- | --- |
| `too_low` | 實測角度低於參考且超標 |
| `too_high` | 實測角度高於參考且超標 |
| `within_tolerance` | 在容許差內 |
| `unavailable` | 無法計算 |

每個狀態至少需要一句非空文字，可使用 `{pose}` 和 `{joint}`。後端會附上實測、參考與調整角度，並把偏差較大的建議排在前面。

句庫路徑由 `FEEDBACK_JSON_PATH` 設定，預設為 `data/pose_feedback_fix.json`。修改句庫後重新啟動後端。

參考角度的執行依據是 CSV 與 `comparison`；JSON 內的 `reference_deg` 是一致性快照，不應單獨修改。
