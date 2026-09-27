# yoga_MIX V3 修改說明

## 這版改了什麼

V2 的藍色導引線是由 `reference_deg`（正解角度）搭配使用者目前 Landmark，以三角函數重新推算 endpoint 後繪製。

V3 改為：

1. 從既有正解 CSV 載入真正的 33 點 reference landmarks。
2. 使用與 `Normalizer` 相同的髖中心／肩中心與 pose scale 規則，把正解骨架對齊到使用者照片。
3. 藍色實線直接畫「對齊後的正解 Landmark 骨架」，不再用角度推算藍線方向。
4. LightGBM、MediaPipe、八角度判定、紅綠點、評分與文字回饋邏輯維持原本 V2。
5. 戰士二式／樹式若角度比較選到左右鏡像參考，藍色正解骨架也同步鏡像。
6. 增加離畫面過遠的防護，避免異常座標產生跨畫面的藍線。

## 主要修改檔案

- `backend/utils/pose_visualization.py`
  - 新增 `_user_center_and_scale()`
  - 新增 `aligned_reference_landmarks()`
  - `render_prediction()` 改為直接繪製 reference landmarks
- `backend/utils/pose_comparison.py`
  - 新增 `reference_mirrored`，讓可左右互換的姿勢知道實際採用哪個參考方向
- `backend/app/routes.py`
  - 照片與影片分析繪圖時，把該姿勢的 `reference_poses` 傳給視覺化函式

## 未修改

分類模型 `anglediff_lightgbm.joblib`、MediaPipe 模型、正解 CSV、角度容許差與前端版面均未更換。
