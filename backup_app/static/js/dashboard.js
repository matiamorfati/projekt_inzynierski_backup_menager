let allBackups = [];

function formatDateNoSeconds(dateString) {
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
      "<tr><td colspan='4'>Brak danych do wyświetlenia</td></tr>";
    return;
  }

  const limitedBackups = backups.slice(0, 3);

  function formatBytes(bytes) {
    if (bytes === null || bytes === undefined) return "-";
    const thresh = 1024;
    let u = 0;
    const units = ["B", "KB", "MB", "GB", "TB"];
    let val = Number(bytes);
    if (isNaN(val)) return "-";
    while (val >= thresh && u < units.length - 1) {
      val = val / thresh;
      u++;
    }
    return u === 0 ? `${val} ${units[u]}` : `${val.toFixed(1)} ${units[u]}`;
  }

  tableBody.innerHTML = limitedBackups
    .map((backup) => {
      const statusOk = (backup.status || "").toUpperCase() === "OK";
      const statusClass = statusOk ? "confirmed" : "failed";
      const statusLabel = statusOk ? "Succeeded" : backup.status || "Failed";

      const formattedDate = formatDateNoSeconds(backup.date);
      return `
              <tr>
                <td>${backup.custom_name}</td>
                <td>${formattedDate}</td>
                <td>${formatBytes(backup.size)}</td>
                <td class="status ${statusClass}">${
        statusOk ? "✔" : "✖"
      } <span>${statusLabel}</span></td>
              </tr>
            `;
    })
    .join("");
}

async function fetchHistory() {
  const tableBody = document.getElementById("history-table-body");
  tableBody.innerHTML = "<tr><td colspan='4'>Loading…</td></tr>";

  try {
    const response = await fetch("/api/backups/history/?limit=50");
    if (!response.ok) {
      throw new Error("Nie udało się pobrać historii");
    }

    const data = await response.json();
    allBackups = data.backups || [];
    renderHistory(allBackups);
  } catch (error) {
    console.error(error);
    tableBody.innerHTML =
      "<tr><td colspan='4'>Nie udało się pobrać historii</td></tr>";
    showError();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  fetchHistory();
});
