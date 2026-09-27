# 前端資料夾差異比較

比較日期：2026-09-26

## 比較範圍

| 版本 | 資料夾 |
|---|---|
| 目前版本 | `C:\Users\vgohu\Desktop\yoga_MIX (1)\yoga_MIX\frontend` |
| 比較版本 | `C:\Users\vgohu\Desktop\yoga_MIX\yoga_MIX\frontend` |

以下以「目前版本」相對於「比較版本」說明。這是檔案內容比較，不是 Git 修改紀錄，無法據此判定修改時間或作者。「新增」表示只存在於目前版本；「缺少」表示只存在於比較版本。

程式與資源檔統計排除虛擬環境、`__pycache__`、`.pyc` 與執行日誌。

## 差異統計

| 類型 | 檔案數量 |
|---|---:|
| 內容修改 | 12 |
| 目前版本新增 | 3 |
| 目前版本缺少 | 4 |
| 內容完全相同 | 55 |

## 修改的檔案

以下路徑均相對於各自的 `frontend` 資料夾。

| 檔案 | 目前版本的差異 |
|---|---|
| `main.py` | 將影片時間軸移至結果卡片內，傳入目前影格、最大影格數、時間資訊與滑動回呼；分析完成改用通知顯示；新增「調整姿勢再重新拍攝」的結果顯示處理。移除原本獨立的狀態文字與時間軸區塊。 |
| `components/result_display_card.py` | 新增紅綠點與螢光藍線的說明；整合影片時間軸、影格資訊與建議更新時間；呼叫 `normalize_result()`；無評分時仍顯示回饋，姿勢名稱為空則不顯示。 |
| `components/pose_carousel.py` | 示範影片順序由「下犬式 → 戰士二式 → 樹式 → 棒式 → 女神式」改為「下犬式 → 樹式 → 棒式 → 女神式 → 戰士二式」。 |
| `components/upload_section.py` | 上傳容量限制與支援格式由一行拆成兩行；移除註解中的舊按鈕程式。實際上傳限制未變更。 |
| `components/__init__.py` | 移除 `result_display_dots`、`result_display_bars` 的匯入與匯出。 |
| `schemas/__init__.py` | 移除 `DetectionResponse`、`Detection`、`Landmark` 的匯入與匯出，保留 `MediaCard`。 |
| `services/video_timeline.py` | 無法評分的影格不再沿用前面的回饋；沒有辨識結果時，姿勢名稱設為空白，無法分析原因放入回饋；尋找歷史回饋時跳過無分數的影格。 |
| `static/css/pose_carousel.css` | 縮窄輪播卡片、取消陰影與 CSS 縮放，調整手機和平板版型，簡化部分響應式設定。 |
| `static/js/pose_carousel.js` | 新增卡片間距 40；切換速度由 350 改為 400；立體效果 modifier 由 2.5 改為 1.5；啟用版面變動監測；只有中央影片可操作，兩側影片自動暫停。 |
| `static/css/style.css` | 僅註解與空白整理，實際樣式規則相同。 |
| `tests/test_frontend.py` | 更新無評分影格與時間軸測試，新增後端連線失敗測試；配合結果卡片重建時間軸的行為重新取得滑桿。 |
| `web/index.html` | 分數檢查由 `Number.isInteger()` 改為 `Number.isFinite()`，可顯示 3.5、4.5 等小數分數。 |

## 目前版本新增的檔案

| 檔案 | 用途 |
|---|---|
| `services/result_feedback.py` | 定義「調整姿勢再重新拍攝」訊息；`normalize_result()` 目前只複製結果，不修改後端判斷。 |
| `tests/test_lotus_score.py` | 檢查完整、半朵與空白蓮花的分數顯示，以及半朵蓮花圖片是否存在。 |
| `tests/test_unrated_result.py` | 檢查後端判斷的保留、無評分結果、零分，以及避免沿用舊回饋。 |

## 比較版本有、目前版本沒有的檔案

| 檔案 | 相關差異 |
|---|---|
| `components/result_display_bars.py` | 目前版本亦移除了對應元件匯入與匯出。 |
| `components/result_display_dots.py` | 目前版本亦移除了對應元件匯入與匯出。 |
| `components/score_indicator.py` | 目前版本不存在此檔案。 |
| `schemas/analysis.py` | 目前版本亦移除了相關分析資料模型的匯入與匯出。 |

## 相同的主要檔案與資源

以下內容在兩份資料夾中相同：

- 設定與文件：`.env`、`requirements.txt`、`README.md`、`web/config.js`。
- API 串接：`services/api_client.py`。
- 相機與上傳 JavaScript：`components/camera_capture.py`、`static/js/camera.js`、`static/js/upload_dropzone.js`。
- 蓮花評分元件：`components/lotus_score.py`。目前版本新增了對應測試，但元件本身相同。
- 首頁與共用元件：`components/hero_section.py`、`components/nav_bar.py`、`components/footer.py`、`components/loading_screen.py`、`components/marquee_slider.py`、`components/message_banner.py`、`components/cursor_wheel.py`。
- 簡易介面：`nicegui/main_n.py`。
- 媒體資料模型：`schemas/media.py`。
- 圖片、蓮花圖片與示範影片，包括 `static/videos/old/` 中的影片。

## 執行環境與產生檔案

這些差異未計入上方程式與資源檔統計。

| 項目 | 目前版本 | 比較版本 |
|---|---|---|
| 虛擬環境位置 | `frontend\.venv` | `frontend\frontend`，內含 `pyvenv.cfg` |
| 執行日誌 | 多出下列四個日誌檔案 | 沒有對應日誌檔案 |

目前版本多出的日誌：

- `nicegui.stderr.log`
- `nicegui.stdout.log`
- `server.stderr.log`
- `server.stdout.log`

虛擬環境套件與 Python 快取未逐項比較；不同環境位置不代表前端功能本身的修改。

## 與近期螢光藍線修改的關係

角度修正、肢段長度保留、四點連線，以及女神式手肘向上彎折，主要實作位於目前專案的 `backend/utils/pose_visualization.py`，不在本次前端比較範圍內。

前端與這些修改直接相關的差異，是 `components/result_display_card.py` 新增的說明文字：

> 綠點：角度合格｜紅點：相關角度超標｜螢光藍色粗實線：正確角度連線，相鄰關節同時超標時合併為四點連線（達容忍範圍即消失）

前端顯示後端回傳的骨架圖片；僅複製前端資料夾，並不會一併帶入後端的藍線繪製邏輯。
