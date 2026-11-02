const token = localStorage.getItem("token");

function riskBadgeClass(risk) {
  if (risk >= 60) return "high";
  if (risk >= 40) return "med";
  return "low";
}

function renderRow(tx, withUser) {
  const row = document.createElement("tr");

  const idCell = document.createElement("td");
  idCell.className = "mono";
  idCell.textContent = tx.id;
  row.appendChild(idCell);

  if (withUser) {
    const userCell = document.createElement("td");
    userCell.textContent = tx.user_id || "—";
    row.appendChild(userCell);
  }

  const payeeCell = document.createElement("td");
  payeeCell.textContent = tx.payee_name || tx.payee_vpa || "—";
  row.appendChild(payeeCell);

  const amountCell = document.createElement("td");
  amountCell.className = "mono";
  amountCell.textContent = `₹${tx.amount}`;
  row.appendChild(amountCell);

  const statusCell = document.createElement("td");
  const statusTag = document.createElement("span");
  statusTag.className = `status-tag ${tx.status}`;
  statusTag.textContent = (tx.status || "").replaceAll("_", " ");
  statusCell.appendChild(statusTag);
  row.appendChild(statusCell);

  const riskCell = document.createElement("td");
  const riskBadge = document.createElement("span");
  riskBadge.className = `risk-badge ${riskBadgeClass(tx.risk || 0)}`;
  riskBadge.textContent = `${tx.risk || 0}%`;
  riskCell.appendChild(riskBadge);
  row.appendChild(riskCell);

  if (withUser) {
    const locCell = document.createElement("td");
    locCell.textContent = tx.location_is_new_for_user ? "⚠️ New location" : (tx.latitude ? "Known" : "—");
    row.appendChild(locCell);
  }

  return row;
}

async function loadTransactions() {
  const res = await fetch(`${API_BASE}/transactions/all`, {
    headers: { Authorization: "Bearer " + token }
  });

  if (res.status === 401 || res.status === 403) {
    alert("Owner access required");
    window.location.href = "../login.html";
    return;
  }

  const data = await res.json();

  const fullTable = document.getElementById("txTable");
  const recentTable = document.getElementById("txTableRecent");

  fullTable.innerHTML = "";
  recentTable.innerHTML = "";

  if (!Array.isArray(data) || data.length === 0) {
    fullTable.innerHTML = '<tr><td colspan="7" class="console-empty">No transactions yet.</td></tr>';
    recentTable.innerHTML = '<tr><td colspan="5" class="console-empty">No transactions yet.</td></tr>';
    return;
  }

  data.forEach(tx => fullTable.appendChild(renderRow(tx, true)));
  data.slice(0, 6).forEach(tx => recentTable.appendChild(renderRow(tx, false)));
}

async function loadSummary() {
  const res = await fetch(`${API_BASE}/analytics/summary`, {
    headers: { Authorization: "Bearer " + token }
  });
  if (!res.ok) return;
  const data = await res.json();

  document.getElementById("statTotal").innerText = data.total_transactions ?? "0";
  document.getElementById("statFraud").innerText = data.fraud_transactions ?? "0";
  document.getElementById("statSafe").innerText = data.safe_transactions ?? "0";
  document.getElementById("statRate").innerText = `${data.fraud_percentage ?? 0}%`;
}

window.onload = () => {
  loadTransactions();
  loadSummary();
};
