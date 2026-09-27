function initUploadDropzone() {
  const dropzone = document.querySelector(".upload-dropzone");
  // 尋找 NiceGUI 內部帶有的真實 file input
  const fileInput = document.querySelector(".upload-dropzone input[type='file']") || document.querySelector("input[type='file']");

  if (!dropzone || !fileInput) {
    setTimeout(initUploadDropzone, 50);
    return;
  }
  if (dropzone.dataset.dropzoneReady) return;
  dropzone.dataset.dropzoneReady = "true";

  // 1. 點擊自訂框 -> 觸發檔案選擇
  dropzone.addEventListener("click", (e) => {
    // 避免重複觸發
    if (e.target.tagName !== 'INPUT') {
      fileInput.click();
    }
  });

  // 2. 徹底阻止瀏覽器預設的「拖曳開圖檔」行為
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    }, false);
  });

  // 3. 加上視覺回饋樣式（可選）
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => {
      dropzone.classList.add("upload-dropzone--dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => {
      dropzone.classList.remove("upload-dropzone--dragover");
    });
  });

  // 4. 關鍵：當把檔案「放開 (drop)」時，指定給 fileInput 並手動發送 change 事件
  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer && e.dataTransfer.files;
    if (files && files.length > 0) {
      fileInput.files = files; // 將拖曳的檔案指派給原生的 input
      
      // 觸發 change 事件讓 NiceGUI / 系統知道檔案已選擇
      const event = new Event('change', { bubbles: true });
      fileInput.dispatchEvent(event);
    }
  });
}

if (document.readyState === "complete") {
  initUploadDropzone();
} else {
  window.addEventListener("load", initUploadDropzone);
}

