document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("create-backup-form");
  const sourcesInput = document.getElementById("sources");
  const destinationInput = document.getElementById("destination");
  const messageEl = document.getElementById("form-message");
  const submitBtn = document.getElementById("create-backup-btn");
  const destinationRow = document.getElementById("destination-row");
  const destinationModeRadios = document.querySelectorAll(
    'input[name="destinationMode"]'
  );
  const browseSourcesBtn = document.getElementById("browse-sources");
  const browseDestinationBtn = document.getElementById("browse-destination");

  if (!form) {
    console.warn("create-backup-form not found on page");
    return;
  }

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

  const updateDestinationVisibility = () => {
    const selected = document.querySelector(
      'input[name="destinationMode"]:checked'
    );
    const showDestination = selected && selected.value !== "drive";
    destinationRow.hidden = !showDestination;
    if (!showDestination) {
      destinationInput.value = "";
    }
  };

  const pickDirectory = async () => {
    if (window.showDirectoryPicker) {
      try {
        const handle = await window.showDirectoryPicker();
        return handle.name;
      } catch (error) {
        if (error?.name !== "AbortError") {
          console.warn("Directory picker error", error);
        }
        return null;
      }
    }

    return new Promise((resolve) => {
      const input = document.createElement("input");
      input.type = "file";
      input.webkitdirectory = true;
      input.addEventListener("change", () => {
        if (!input.files || input.files.length === 0) {
          resolve(null);
          return;
        }
        const file = input.files[0];
        const relativePath = file.webkitRelativePath || "";
        const folderName = relativePath.split("/")[0] || file.name;
        resolve(folderName);
      });
      input.click();
    });
  };

  const pickSources = async () => {
    const collected = [];

    if (window.showDirectoryPicker) {
      try {
        const dirHandle = await window.showDirectoryPicker();
        collected.push(dirHandle.name);
      } catch (error) {
        if (error?.name !== "AbortError") {
          console.warn("Directory picker error", error);
        }
      }
    }

    if (collected.length === 0 && window.showOpenFilePicker) {
      try {
        const handles = await window.showOpenFilePicker({ multiple: true });
        for (const handle of handles) {
          collected.push(handle.name);
        }
      } catch (error) {
        if (error?.name !== "AbortError") {
          console.warn("File picker error", error);
        }
      }
    }

    if (collected.length === 0) {
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = true;
      input.webkitdirectory = true;
      return new Promise((resolve) => {
        input.addEventListener("change", () => {
          if (!input.files) {
            resolve([]);
            return;
          }
          const paths = Array.from(input.files).map((file) => {
            const relative = file.webkitRelativePath || "";
            return relative.split("/")[0] || file.name;
          });
          resolve(paths);
        });
        input.click();
      });
    }

    return collected;
  };

  destinationModeRadios.forEach((radio) => {
    radio.addEventListener("change", updateDestinationVisibility);
  });

  if (browseDestinationBtn) {
    browseDestinationBtn.addEventListener("click", async () => {
      const folder = await pickDirectory();
      if (folder) {
        destinationInput.value = folder;
      }
    });
  }

  if (browseSourcesBtn) {
    browseSourcesBtn.addEventListener("click", async () => {
      const picks = await pickSources();
      if (picks && picks.length) {
        const existing = sourcesInput.value.trim();
        const current = existing ? existing.split(/[;\n]+/) : [];
        const merged = [...current.filter(Boolean), ...picks];
        sourcesInput.value = merged.join("\n");
      }
    });
  }

  updateDestinationVisibility();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("");
    sourcesInput.classList.remove("input-error");

    const rawSources = sourcesInput.value.trim();
    if (!rawSources) {
      setMessage("Please provide at least one source path.", "error");
      sourcesInput.classList.add("input-error");
      sourcesInput.focus();
      return;
    }

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

    const selectedMode = document.querySelector(
      'input[name="destinationMode"]:checked'
    );
    const modeValue = selectedMode?.value || "drive";

    const payload = {
      sources,
      store_local: modeValue !== "drive",
      upload_to_drive: modeValue !== "local",
    };

    const dest = destinationInput.value.trim();
    if (dest && modeValue !== "drive") {
      payload.destination = dest;
    }

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
        showSuccess();
      } else {
        setMessage(
          "Backup did not start correctly. Check logs and history.",
          "error"
        );
        showError();
      }
    } catch (error) {
      console.error("Error while calling /api/backups/run/:", error);
      setMessage(
        "Unexpected error while calling API. See browser console and backend logs.",
        "error"
      );
      showError();
    } finally {
      setLoading(false);
    }
  });
});

function showSuccess() {
  const el = document.getElementById("status-success");
  if (el) el.style.display = "flex";
}

function showError() {
  const el = document.getElementById("status-error");
  if (el) el.style.display = "flex";
}

function hideStatus() {
  const success = document.getElementById("status-success");
  const error = document.getElementById("status-error");
  if (success) success.style.display = "none";
  if (error) error.style.display = "none";
}
