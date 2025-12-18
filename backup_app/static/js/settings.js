document.addEventListener("DOMContentLoaded", () => {
  /* ============================
     TOGGLES – wizualny stan
  ============================ */

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

  /* ============================
     MAIL NOTIFIER – pokaż/ukryj email
  ============================ */

  const mailCheckbox = document.getElementById("mail-notifier-enabled");
  const mailGroup = document.getElementById("mail-notifier-email-group");

  if (mailCheckbox && mailGroup) {
    const updateMailVisibility = () => {
      mailGroup.style.display = mailCheckbox.checked ? "block" : "none";
    };

    updateMailVisibility();
    mailCheckbox.addEventListener("change", updateMailVisibility);
  }

  /* ============================
     AUTO BACKUP FORM
  ============================ */

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

  /* ============================
     USER CONFIG FORM
  ============================ */


  const userForm = document.getElementById("user-config-form");

  if (userForm) {
    userForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      // Pobierz dane z formularza
      const payload = {
        name: document.getElementById("profile-name")?.value.trim(),
        sources: document.getElementById("profile-sources")?.value.trim().split(';').map(s => s.trim()).filter(Boolean),
        backup_directory: document.getElementById("profile-backup-directory")?.value.trim(),
        restore_directory: document.getElementById("profile-restore-directory")?.value.trim(),
        backup_frequency: document.getElementById("profile-backup-frequency")?.value,
        daily_report_enable: document.getElementById("profile-daily-report-enable")?.checked,
        daily_report_time: document.getElementById("profile-daily-report-time")?.value,
        recipient_email: document.getElementById("profile-recipient-email")?.value.trim(),
        is_default: document.getElementById("profile-is-default")?.checked,
        custom_name: document.getElementById("profile-custom-name")?.value.trim(),
        description: document.getElementById("profile-description")?.value.trim(),
      };

      try {
        const res = await fetch("/api/create_backup_profile/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          },
          body: JSON.stringify(payload),
        });

        if (!res.ok) throw new Error("Profile creation failed");

        showSuccess();
      } catch (err) {
        console.error(err);
        showError();
      }
    });
  }
});

/* ============================
   STATUS OVERLAYS
============================ */

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

/* ============================
   CSRF – Django helper
============================ */

function getCSRFToken() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
}
