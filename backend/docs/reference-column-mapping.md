# CSV 參考欄位

參考資料位於 `utils/yoga_5poses_mediapipe_dataset_complete.csv`。

- `pose_class`：姿勢類別。
- `lm_0_x`～`lm_32_z`：MediaPipe 33 個 Landmark。
- `L/R_elbow_angle`：左右肘。
- `L/R_shoulder_angle`：左右肩。
- `L/R_hip_angle`：左右髖。
- `L/R_knee_angle`：左右膝。

分類特徵使用 23 個點的 xyz 座標與 7 個角度，共 76 維。標準判定則使用 CSV 的八項角度，兩者用途不同。

CSV 每種姿勢只能有一筆。載入時會驗證欄位、姿勢、座標、角度及由座標重算的角度一致性。

樹式與戰士二式的換邊參考由程式成對互換 L/R 角度，CSV 不需要新增第二筆。回傳的關節名稱仍代表使用者實際身體側。
