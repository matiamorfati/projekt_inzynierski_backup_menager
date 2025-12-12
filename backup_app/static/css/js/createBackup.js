document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("create-backup-form");
  const sourcesInput = document.getElementById("sources");
  const destinationInput = document.getElementById("destination");
  const uploadSelect = document.getElementById("uploadToDrive");
  const messageEl = document.getElementById("form-message");
  const submitBtn = document.getElementById("create-backup-btn");

  if (!form) {
    console.warn("create-backup-form not found on page");
    return;
  }

  const setMessage = (text, type) => {
    messageEl.textContent = text || "";
    messageEl.className = "form-message"; // reset klas
    if (type) {
      messageEl.classList.add(
        type === "error" ? "form-message-error" : "form-message-success"
      );
    }
  };

  const setLoading = (isLoading) => {
    if (!submitBtn) return;
    submitBtn.disabled = isLoading;
    submitBtn.classList.toggle("btn-loading", isLoading);
    submitBtn.textContent = isLoading ? "Working..." : "+ Create backup";
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("");
    sourcesInput.classList.remove("input-error");

    // PROSTA WALIDACJA
    const rawSources = sourcesInput.value.trim();
    if (!rawSources) {
      setMessage("Please provide at least one source path.", "error");
      sourcesInput.classList.add("input-error");
      sourcesInput.focus();
      return;
    }

    // Rozbijamy po ; lub nowej linii
    const sources = rawSources
      .split(/[;\n]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    if (sources.length === 0) {
      setMessage(
        "Sources field is empty after parsing. Check separators (; or new lines).",
        "error"
      );
      sourcesInput.classList.add("input-error");
      sourcesInput.focus();
      return;
    }

    const payload = { sources: sources };

    const dest = destinationInput.value.trim();
    if (dest) {
      payload.destination = dest;
    }

    const uploadRaw = uploadSelect.value;
    if (uploadRaw === "true") {
      payload.upload_to_drive = true;
    } else if (uploadRaw === "false") {
      payload.upload_to_drive = false;
    }
    // wartość "" oznacza: użyj domyślnego CONFIG["enable_drive_upload"]

    setLoading(true);

    try {
      const response = await fetch("/api/backups/run/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const data = await response.json();

      if (data.ok) {
        setMessage("Backup has been started successfully.", "success");
        // opcjonalnie: wyczyść formularz
        // form.reset();
      } else {
        setMessage(
          "Backup did not start correctly. Check logs and history.",
          "error"
        );
      }
    } catch (error) {
      console.error("Error while calling /api/backups/run/:", error);
      setMessage(
        "Unexpected error while calling API. See browser console and backend logs.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  });
});
