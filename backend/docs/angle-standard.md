# 角度判定

系統比較左右肘、肩、髖、膝共八項角度。

| 角度 | 容許差 |
| --- | --- |
| 左右髖 | ±30° |
| 其餘六項 | ±20° |

每項結果位於 `comparison.angles`：

```json
{
  "reference_deg": 90,
  "actual_deg": 115,
  "difference_deg": 25,
  "tolerance_deg": 20,
  "within_tolerance": false
}
```

`comparison.is_standard`：

- `true`：需要評估的角度都合格。
- `false`：至少一項有效角度超標。
- `null`：沒有超標，但資料不足以完整判定。

## 特例

- 樹式與戰士二式會比較原始及整組左右互換的參考，選擇失敗項較少、總偏差較小的一組。
- 下犬式允許側面拍攝；同一側肘、肩、髖、膝可計算，且所有可見角度合格即可通過。
- 其他姿勢需要八項角度完整。

`confidence` 是 LightGBM 分類信心，不能用來判定姿勢是否正確。
