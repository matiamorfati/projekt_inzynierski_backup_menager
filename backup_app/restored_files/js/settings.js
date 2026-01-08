document.addEventListener("DOMContentLoaded", () => {
  function bindToggle(wrapperId, checkboxId) {
    const wrap = document.getElementById(wrapperId);
    const checkbox = document.getElementById(checkboxId);

    if (!wrap || !checkbox) return;

    const update = () => {
      wrap.classList.toggle("on", checkbox.checked);
    };

    update();
    checkbox.addEventListener("change", update);
  }

  bindToggle("autoWrap", "auto-backup-enabled");
  bindToggle("mailWrap", "mail-notifier-enabled");

  const mailCheckbox = document.getElementById("mail-notifier-enabled");
  const mailGroup = document.getElementById("mail-notifier-email-group");

  if (mailCheckbox && mailGroup) {
    const updateMailVisibility = () => {
      mailGroup.style.display = mailCheckbox.checked ? "block" : "none";
    };

    updateMailVisibility();
    mailCheckbox.addEventListener("change", updateMailVisibility);
  }

  const autoForm = document.getElementById("auto-backup-form");

  if (autoForm) {
    autoForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const payload = {
        enabled: document.getElementById("auto-backup-enabled")?.checked,
        destination: document.getElementById("auto-backup-type")?.value,
        local_path: document.getElementById("auto-local-path")?.value.trim(),
        source_path: document.getElementById("auto-source-path")?.value.trim(),
        frequency: document.getElementById("auto-frequency")?.value,
        time: document.getElementById("auto-time")?.value,
      };

      try {
        const res = await fetch("/api/settings/auto-backup/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          },
          body: JSON.stringify(payload),
        });

        if (!res.ok) throw new Error("Auto-backup save failed");

        showSuccess();
      } catch (err) {
        console.error(err);
        showError();
      }
    });
  }

  const userForm = document.getElementById("user-config-form");

  if (userForm) {
    userForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const payload = {
        mail_notifier_enabled: document.getElementById("mail-notifier-enabled")
          ?.checked,
        notification_email: document
          .getElementById("mail-notifier-email")
          ?.value.trim(),
        default_local_path: document
          .getElementById("user-local-path")
          ?.value.trim(),
        theme: document.getElementById("theme-mode")?.value,
      };

      try {
        const res = await fetch("/api/settings/user/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          },
          body: JSON.stringify(payload),
        });

        if (!res.ok) throw new Error("User settings save failed");

        showSuccess();
      } catch (err) {
        console.error(err);
        showError();
      }
    });
  }
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

function getCSRFToken() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
}
