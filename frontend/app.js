(() => {
  "use strict";

  const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg"]);
  const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB, backend ile aynı sınır

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const errorMessage = document.getElementById("error-message");
  const filePreview = document.getElementById("file-preview");
  const fileThumbnail = document.getElementById("file-thumbnail");
  const fileNameEl = document.getElementById("file-name");
  const fileSizeEl = document.getElementById("file-size");
  const removeFileButton = document.getElementById("remove-file");
  const loadingIndicator = document.getElementById("loading");
  const resultsSection = document.getElementById("results");

  let selectedFile = null;
  let thumbnailUrl = null;

  function formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    const units = ["KB", "MB", "GB"];
    let value = bytes / 1024;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex += 1;
    }
    return `${value.toFixed(1)} ${units[unitIndex]}`;
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
  }

  function clearError() {
    errorMessage.hidden = true;
    errorMessage.textContent = "";
  }

  function setLoading(isLoading) {
    loadingIndicator.hidden = !isLoading;
  }

  function clearResults() {
    resultsSection.hidden = true;
    resultsSection.innerHTML = "";
  }

  function resetSelection() {
    selectedFile = null;
    if (thumbnailUrl) {
      URL.revokeObjectURL(thumbnailUrl);
      thumbnailUrl = null;
    }
    fileInput.value = "";
    filePreview.hidden = true;
    fileThumbnail.src = "";
    clearResults();
    setLoading(false);
  }

  function validateFile(file) {
    if (!ACCEPTED_TYPES.has(file.type)) {
      return `Desteklenmeyen dosya türü: '${file.type || "bilinmiyor"}'. Yalnızca PNG veya JPEG kabul edilir.`;
    }
    if (file.size === 0) {
      return "Seçilen dosya boş (0 bayt).";
    }
    if (file.size > MAX_FILE_SIZE) {
      return `Dosya çok büyük: ${formatFileSize(file.size)} (üst sınır ${formatFileSize(MAX_FILE_SIZE)}).`;
    }
    return null;
  }

  function showFilePreview(file) {
    if (thumbnailUrl) {
      URL.revokeObjectURL(thumbnailUrl);
    }
    thumbnailUrl = URL.createObjectURL(file);
    fileThumbnail.src = thumbnailUrl;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = formatFileSize(file.size);
    filePreview.hidden = false;
  }

  function handleFile(file) {
    clearError();
    clearResults();

    const validationError = validateFile(file);
    if (validationError) {
      showError(validationError);
      filePreview.hidden = true;
      selectedFile = null;
      return;
    }

    selectedFile = file;
    showFilePreview(file);
    // NOT: /api/v1/analyze entegrasyonu (fetch + loading göstergesinin
    // gerçek istekle birlikte kullanılması) Gün 17 kapsamındadır.
  }

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("dropzone--dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dropzone--dragover");
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("dropzone--dragover");
    const [file] = event.dataTransfer.files;
    if (file) {
      handleFile(file);
    }
  });

  fileInput.addEventListener("change", () => {
    const [file] = fileInput.files;
    if (file) {
      handleFile(file);
    }
  });

  removeFileButton.addEventListener("click", (event) => {
    event.stopPropagation();
    resetSelection();
  });
})();
