let allBackups = [];

function formatDateNoSeconds(dateString) {
  // Obsługuje formaty ISO i inne typowe
  const date = new Date(dateString);
  if (isNaN(date)) return dateString;
  // yyyy-mm-dd HH:MM
  return (
    date.getFullYear() +
    "-" +
    String(date.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(date.getDate()).padStart(2, "0") +
    " " +
    String(date.getHours()).padStart(2, "0") +
    ":" +
    String(date.getMinutes()).padStart(2, "0")
  );
}

function renderHistory(backups) {
  const tableBody = document.getElementById("history-table-body");
  if (backups.length === 0) {
    tableBody.innerHTML =
      "<tr><td colspan='5'>Brak danych do wyświetlenia</td></tr>";
    return;
  }
  tableBody.innerHTML = backups
    .map((backup) => {
      const statusOk = (backup.status || "").toUpperCase() === "OK";
      const statusClass = statusOk ? "confirmed" : "failed";
      const statusLabel = statusOk ? "Succeeded" : backup.status || "Failed";
      const description = backup.description?.trim()
        ? backup.description
        : "Brak opisu";
      // Format date without seconds
      const formattedDate = formatDateNoSeconds(backup.date);
      return `
              <tr>
                <td>${backup.name}</td>
                <td>${formattedDate}</td>
                <td>${description}</td>
                <td class="status ${statusClass}">${
        statusOk ? "✔" : "✖"
      } <span>${statusLabel}</span></td>
                <td>
                  <button class="btn-primary restore-btn" data-name="${
                    backup.name
                  }">Restore</button>
                </td>
              </tr>
            `;
    })
    .join("");
}

function filterAndRender() {
  const searchInput = document.querySelector(".search");
  const filterSelect = document.querySelector(".status-filter");
  const searchValue = searchInput.value.trim().toLowerCase();
  const filterValue = filterSelect.value;

  let filtered = allBackups;
  if (searchValue) {
    filtered = filtered.filter(
      (b) =>
        (b.name && b.name.toLowerCase().includes(searchValue)) ||
        (b.date && b.date.toLowerCase().includes(searchValue))
    );
  }
  if (filterValue === "Confirmed") {
    filtered = filtered.filter((b) => (b.status || "").toUpperCase() === "OK");
  } else if (filterValue === "Failed") {
    filtered = filtered.filter((b) => (b.status || "").toUpperCase() !== "OK");
  }
  renderHistory(filtered);
}

async function fetchHistory() {
  const tableBody = document.getElementById("history-table-body");
  tableBody.innerHTML = "<tr><td colspan='5'>Loading…</td></tr>";

  try {
    const response = await fetch("/api/backups/history/?limit=50");
    if (!response.ok) {
      throw new Error("Nie udało się pobrać historii");
    }

    const data = await response.json();
    allBackups = data.backups || [];
    filterAndRender();
  } catch (error) {
    console.error(error);
    tableBody.innerHTML =
      "<tr><td colspan='5'>Nie udało się pobrać historii</td></tr>";
    showError();
  }
}

async function handleRestore(backupName) {
  try {
    const response = await fetch("/api/restore/full/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ backup_name: backupName }),
    });

    const data = await response.json();
    if (response.ok && data.ok) {
      showSuccess();
    } else {
      showError();
    }
  } catch (error) {
    console.error("Błąd podczas przywracania:", error);
    showError();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const tableBody = document.getElementById("history-table-body");
  const searchInput = document.querySelector(".search");
  const filterSelect = document.querySelector(".status-filter");

  tableBody.addEventListener("click", (event) => {
    const button = event.target.closest(".restore-btn");
    if (!button) return;

    const backupName = button.getAttribute("data-name");
    if (backupName) {
      handleRestore(backupName);
    }
  });

  if (searchInput) {
    searchInput.addEventListener("input", filterAndRender);
  }
  if (filterSelect) {
    filterSelect.addEventListener("change", filterAndRender);
  }

  fetchHistory();
});
