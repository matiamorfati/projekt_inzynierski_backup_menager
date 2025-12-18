document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("create-backup-form");

  const sourcesInput = document.getElementById("sources");
  const sourcesSummary = document.getElementById("sources-summary");

  const descriptionInput = document.getElementById("description");
  const backupTypeSelect = document.getElementById("backupType");
  const destinationGroup = document.getElementById("destination-group");
  const destinationInput = document.getElementById("destination");
  const textareas = document.querySelectorAll(".auto-resize");

  const messageEl = document.getElementById("form-message");
  const submitBtn = form?.querySelector("button[type='submit']");

  const sourcePickerBtn = document.getElementById("sources-picker-btn");
  const sourcePicker = document.getElementById("sourcesPicker");

  const destinationPicker = document.getElementById("destinationPicker");
  const destinationPickerBtn = document.getElementById(
    "destination-picker-btn"
  );

  if (!form) {
    console.warn("create-backup-form not found on page");
    return;
  }

  /* ----------------------------
     Helpers
  ---------------------------- */

  // Auto-resize textareas = document.querySelectorAll(".auto-resize");for description
  textareas.forEach((textarea) => {
    textarea.addEventListener("input", () => {
      textarea.style.height = "auto"; // reset
      textarea.style.height = textarea.scrollHeight + "px";
    });
  });

  const setMessage = (text, type) => {
    messageEl.textContent = text || "";
    messageEl.className = "form-message";
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

  sourcePickerBtn?.addEventListener("click", () => {
    sourcesInput?.click();
  });

  // Source picker button opens file input
  sourcePickerBtn?.addEventListener("click", () => {
    sourcePicker?.click();
  });

  // After picking folders, add root folder(s) to the textarea (append, unique, each in new line)
  sourcePicker?.addEventListener("change", () => {
    if (!sourcePicker.files.length) {
      return;
    }
    // Get unique root folders from picker
    const pickedRoots = Array.from(
      new Set(
        Array.from(sourcePicker.files).map(
          (file) => file.webkitRelativePath.split("/")[0]
        )
      )
    );
    // Get current paths from textarea (split by new lines or semicolons)
    const current = sourcesInput.value
      .split(/[;\n]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    // Merge and deduplicate
    const all = Array.from(new Set([...current, ...pickedRoots]));
    sourcesInput.value = all.join("\n");
  });

  /* ----------------------------
     Source folders summary
  ---------------------------- */

  // Show summary of how many folders are in the textarea
  const updateSourcesSummary = () => {
    const folders = sourcesInput.value
      .split(/[\n;]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    sourcesSummary.textContent =
      folders.length > 0
        ? `${folders.length} folder(s) selected`
        : "No folders selected";
  };

  sourcesInput.addEventListener("input", updateSourcesSummary);
  // Also update summary after picking folders
  sourcePicker?.addEventListener("change", updateSourcesSummary);

  // Initial summary update (in case of pre-filled textarea)
  updateSourcesSummary();

  /* ----------------------------
     Backup type → destination toggle
  ---------------------------- */

  backupTypeSelect.addEventListener("change", () => {
    const value = backupTypeSelect.value;
    const needsLocal = value === "local" || value === "both";

    destinationGroup.classList.toggle("hidden", !needsLocal);
  });

  destinationPickerBtn?.addEventListener("click", () => {
    destinationPicker?.click();
  });

  destinationPicker?.addEventListener("change", () => {
    if (!destinationPicker.files.length) {
      destinationInput.value = "";
      return;
    }

    const rootFolder =
      destinationPicker.files[0].webkitRelativePath.split("/")[0];

    destinationInput.value = rootFolder;
  });

  /* ----------------------------
     Submit
  ---------------------------- */

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("");

    /* -------- validation -------- */

    // Parse all folders from textarea (prefer new lines)
    const rawSources = sourcesInput.value.trim();
    const sources = rawSources
      .split(/[\n;]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    if (sources.length === 0) {
      setMessage("Please provide at least one source directory.", "error");
      sourcesInput.focus();
      return;
    }

    const backupType = backupTypeSelect.value;
    if (!backupType) {
      setMessage("Please select backup destination type.", "error");
      backupTypeSelect.focus();
      return;
    }

    if (
      (backupType === "local" || backupType === "both") &&
      !destinationInput.value.trim()
    ) {
      setMessage("Please provide local destination folder.", "error");
      destinationInput.focus();
      return;
    }

    /* -------- payload -------- */

    const payload = {
      sources,
      backup_type: backupType,
    };

    const description = descriptionInput.value.trim();
    if (description) {
      payload.description = description;
    }

    if (backupType === "local" || backupType === "both") {
      payload.destination = destinationInput.value.trim();
    }

    if (backupType === "drive") {
      payload.upload_to_drive = true;
    }

    if (backupType === "local") {
      payload.upload_to_drive = false;
    }

    /* -------- request -------- */

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
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.ok) {
        setMessage("Backup has been started successfully.", "success");
        // form.reset(); // opcjonalnie
        // sourcesSummary.textContent = "No folders selected";
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
