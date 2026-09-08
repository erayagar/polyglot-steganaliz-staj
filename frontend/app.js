(() => {
  "use strict";

  const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg"]);
  const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB, backend ile aynı sınır
  const API_BASE_URL = "http://127.0.0.1:8000";

  const THREAT_LOW_MAX = 33; // 0-33: düşük (yeşil)
  const THREAT_MEDIUM_MAX = 66; // 34-66: orta (sarı), 67-100: yüksek (kırmızı)

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
  let activeAnalysisController = null;

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
    if (activeAnalysisController) {
      activeAnalysisController.abort();
      activeAnalysisController = null;
    }
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

  function threatLevelClass(score) {
    if (score <= THREAT_LOW_MAX) return "threat--low";
    if (score <= THREAT_MEDIUM_MAX) return "threat--medium";
    return "threat--high";
  }

  function renderResults(data) {
    resultsSection.innerHTML = "";

    const badge = document.createElement("div");
    badge.className = `result-badge ${data.polyglot_status ? "result-badge--danger" : "result-badge--success"}`;
    badge.textContent = data.polyglot_status ? "Polyglot tespit edildi" : "Temiz dosya";
    resultsSection.appendChild(badge);

    const levelClass = threatLevelClass(data.threat_score);

    const scoreRow = document.createElement("div");
    scoreRow.className = "threat-score";
    scoreRow.innerHTML = `<span>Tehdit skoru</span><span class="threat-score__value ${levelClass}">${data.threat_score}/100</span>`;
    resultsSection.appendChild(scoreRow);

    const bar = document.createElement("div");
    bar.className = "threat-bar";
    const fill = document.createElement("div");
    fill.className = `threat-bar__fill ${levelClass}`;
    fill.style.width = `${data.threat_score}%`;
    bar.appendChild(fill);
    resultsSection.appendChild(bar);

    const summary = document.createElement("p");
    summary.className = "result-summary";
    summary.textContent = data.analysis_summary;
    resultsSection.appendChild(summary);

    if (data.extracted_video_url) {
      const videoWrapper = document.createElement("div");
      videoWrapper.className = "result-video";
      const video = document.createElement("video");
      video.controls = true;
      video.src = `${API_BASE_URL}${data.extracted_video_url}`;
      videoWrapper.appendChild(video);
      resultsSection.appendChild(videoWrapper);
    }

    resultsSection.hidden = false;
  }

  async function analyzeFile(file) {
    if (activeAnalysisController) {
      activeAnalysisController.abort();
    }
    const controller = new AbortController();
    activeAnalysisController = controller;

    clearError();
    clearResults();
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      if (!response.ok) {
        let detail = `Analiz başarısız oldu (HTTP ${response.status}).`;
        try {
          const errorBody = await response.json();
          if (errorBody && errorBody.detail) {
            detail = errorBody.detail;
          }
        } catch {
          // Yanıt gövdesi JSON değilse varsayılan mesaj kullanılır.
        }
        throw new Error(detail);
      }

      const data = await response.json();
      renderResults(data);
    } catch (error) {
      if (error.name === "AbortError") return;
      showError(error.message || "Sunucuya bağlanılamadı.");
    } finally {
      if (activeAnalysisController === controller) {
        setLoading(false);
        activeAnalysisController = null;
      }
    }
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
    analyzeFile(file);
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
