document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("create-backup-form");

  const sourcesInput = document.getElementById("sources");
  const sourcesSummary = document.getElementById("sources-summary");

  const descriptionInput = document.getElementById("description");
  const backupTypeSelect = document.getElementById("backupType");
  const destinationGroup = document.getElementById("destination-group");
  const destinationInput = document.getElementById("destination");

  const messageEl = document.getElementById("form-message");
  const submitBtn = form?.querySelector("button[type='submit']");

  const fileBtn = document.querySelector(".file-btn");
  if (!form) {
    console.warn("create-backup-form not found on page");
    return;
  }

  /* ----------------------------
     Helpers
  ---------------------------- */

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

  fileBtn?.addEventListener("click", () => {
    sourcesInput?.click();
  });
  /* ----------------------------
     Source folders summary
  ---------------------------- */

  sourcesInput.addEventListener("change", () => {
    if (!sourcesInput.files.length) {
      sourcesSummary.textContent = "No folders selected";
      return;
    }

    const uniqueRoots = new Set(
      Array.from(sourcesInput.files).map(
        (file) => file.webkitRelativePath.split("/")[0]
      )
    );

    sourcesSummary.textContent = `${uniqueRoots.size} folder(s) selected`;
  });

  /* ----------------------------
     Backup type → destination toggle
  ---------------------------- */

  backupTypeSelect.addEventListener("change", () => {
    const value = backupTypeSelect.value;
    const needsLocal = value === "local" || value === "both";

    destinationGroup.classList.toggle("hidden", !needsLocal);
  });

  /* ----------------------------
     Submit
  ---------------------------- */

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("");

    /* -------- validation -------- */

    if (!sourcesInput.files.length) {
      setMessage("Please select at least one source directory.", "error");
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

    /* -------- build sources -------- */

    const sources = Array.from(sourcesInput.files)
      .map((file) => file.webkitRelativePath.split("/")[0])
      .filter((value, index, self) => self.indexOf(value) === index);

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
