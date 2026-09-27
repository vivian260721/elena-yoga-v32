# 圖片與骨架

照片回應包含：

- `original_image`：原圖 Base64 data URL。
- `skeleton_image`：骨架圖 Base64 data URL。
- `image_width`、`image_height`：校正方向後的尺寸。
- `landmarks`：33 個點的座標、可見度與狀態。

前端可直接使用：

```python
original.set_source(data["original_image"])
skeleton.set_source(data["skeleton_image"])
```

骨架顏色：

- 綠色：該點參與的角度都合格。
- 紅色：至少一項參與角度超標。
- 灰色：不可見、未納入八項角度或無法判定。
- 螢光藍色直線虛線：僅為超出容忍值的角度顯示目標肢體方向，以關節為起點，固定近端肢段（肩部固定軀幹），依目前彎曲方向及參考角度繪製。照片與影片逐影格套用，角度合格或無法判定時移除。

虛線沿用評分的正規化影像 x/y 座標計算，投影回原圖；非正方形影像上的視覺角度可能與評分數字不同。每個關節的虛線是獨立方向提示，不是整個人體的重建姿勢。

紅點只代表相關角度超標，不能單憑顏色確定是哪個點造成偏差。
