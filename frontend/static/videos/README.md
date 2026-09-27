放置姿勢選擇 Carousel 用的示範影片（frontend/components/pose_carousel.py 的 DEMO_POSES 對應）。
檔名需對應 frontend/components/pose_carousel.py 中 DEMO_POSES 清單的路徑，例如：
- demo_downdog.mp4
- demo_warrior2.mp4
- demo_tree.mp4
- demo_plank.mp4
- demo_goddess.mp4

影片不會自動播放（<video> 標籤沒有 autoplay 屬性），使用者要自己點擊播放。
建議檔案短一點（5~10 秒的動作示範迴圈）、解析度不用太高，避免 Carousel 捲動時載入太慢。

