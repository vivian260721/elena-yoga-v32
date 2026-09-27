/**
 * camera.js
 * =========
 * 對應需求「或裝置拍攝」：透過瀏覽器 getUserMedia API 開啟裝置相機（手機/電腦鏡頭），
 * 並提供拍照功能，回傳 base64 圖片資料給 NiceGUI 後端（Python）端處理。
 *
 * 由 components/camera_capture.py 透過 ui.add_head_html 載入，
 * 並用 ui.run_javascript() 呼叫下方定義的函式。
 */

let cameraStream = null;

/**
 * 檢查裝置是否有攝影機（對應需求「透過判斷裝置是否有鏡頭顯示使用裝置按鈕」）。
 * 用 enumerateDevices() 列出所有媒體裝置，篩選 kind === 'videoinput'。
 * 這一步不需要使用者先同意權限就能拿到「有沒有攝影機」這個資訊（只是拿不到裝置名稱標籤），
 * 足夠用來決定要不要顯示「使用裝置」按鈕。
 * 結果透過 NiceGUI 的 emitEvent 傳回 Python 端（見 camera_capture.py 的 handle_camera_availability）。
 */
async function checkCameraAvailability() {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      emitEvent("camera_availability_result", { hasCamera: false });
      return;
    }
    const devices = await navigator.mediaDevices.enumerateDevices();
    const hasCamera = devices.some((d) => d.kind === "videoinput");
    emitEvent("camera_availability_result", { hasCamera });
  } catch (err) {
    console.error("偵測攝影機失敗:", err);
    emitEvent("camera_availability_result", { hasCamera: false });
  }
}

/**
 * 開啟裝置相機，將串流畫面接到 <video id="camera-preview"> 元素上。
 * 優先使用後鏡頭 (environment)，找不到則退回預設鏡頭，方便手機直接對著自己拍攝瑜珈動作。
 */
async function startCamera() {
  try {
    // 若已有開啟中的串流，先關閉避免重複佔用鏡頭資源
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop());
    }

    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });

    const videoEl = document.getElementById("camera-preview");
    videoEl.srcObject = cameraStream;
  } catch (err) {
    console.error("開啟相機失敗:", err);
    // 交由呼叫端 (Python) 的 try/except 處理使用者提示，這裡僅記錄錯誤
  }
}

/**
 * 將目前 video 畫面截圖到 canvas，並轉成 base64 JPEG 字串回傳。
 * 回傳格式：data:image/jpeg;base64,xxxxx （與一般 <input type="file"> 上傳格式相容）
 */
function capturePhoto() {
  const videoEl = document.getElementById("camera-preview");
  const canvasEl = document.getElementById("camera-canvas");

  if (!videoEl || !videoEl.videoWidth) {
    return null; // 相機尚未就緒
  }

  canvasEl.width = videoEl.videoWidth;
  canvasEl.height = videoEl.videoHeight;

  const ctx = canvasEl.getContext("2d");
  ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);

  return canvasEl.toDataURL("image/jpeg", 0.9);
}

/**
 * 停止相機串流，釋放鏡頭資源（例如使用者切換離開拍攝分頁時呼叫）
 */
function stopCamera() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
}

/* ---------------------------------------------------------------------- */
/* 錄影功能：對應需求「按鈕『使用裝置』後可選擇拍照或錄影」                    */
/* ---------------------------------------------------------------------- */

let mediaRecorder = null;
let recordedChunks = [];

/**
 * 開始錄影，使用瀏覽器原生 MediaRecorder API 把 cameraStream 錄成 webm 檔。
 * 選 video/webm;codecs=vp9 是因為主流瀏覽器（Chrome/Firefox/Edge）內建支援度最好，
 * 不需要額外安裝任何轉檔套件；後端 core/validators.py 也已經把 .webm 加入允許格式。
 */
function startRecording() {
  if (!cameraStream) {
    console.error("相機尚未啟動，無法開始錄影");
    return;
  }

  recordedChunks = [];
  const options = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
    ? { mimeType: "video/webm;codecs=vp9" }
    : { mimeType: "video/webm" };

  mediaRecorder = new MediaRecorder(cameraStream, options);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data);
    }
  };
  mediaRecorder.start();
}

/**
 * 停止錄影，回傳一個 Promise，resolve 時給出錄好的影片 base64 字串
 * （格式：data:video/webm;base64,xxxxx，與 capturePhoto() 的回傳格式風格一致）。
 * NiceGUI 的 ui.run_javascript() 會自動 await 回傳的 Promise，取得最終結果。
 */
function stopRecording() {
  return new Promise((resolve) => {
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      resolve(null);
      return;
    }

    mediaRecorder.onstop = () => {
      const blob = new Blob(recordedChunks, { type: "video/webm" });
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = () => resolve(null);
      reader.readAsDataURL(blob);
    };

    mediaRecorder.stop();
  });
}
