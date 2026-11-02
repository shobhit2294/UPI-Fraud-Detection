const STATUS_PILL_CLASS = {
  SETTLED: "settled",
  FAILED: "failed",
  STUCK_PENDING_RECONCILIATION: "stuck",
};

function pillClassFor(status) {
  return STATUS_PILL_CLASS[status] || "progress";
}

function labelFor(status) {
  return (status || "PENDING").replaceAll("_", " ");
}

async function loadMyTransactions() {
  const token = localStorage.getItem("token");
  const list = document.getElementById("tx");

  list.innerHTML = "";

  if (!token) {
    list.innerHTML = '<li class="empty-state">Please log in again</li>';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/transactions/my`, {
      headers: { Authorization: "Bearer " + token }
    });

    const data = await res.json();

    if (!res.ok) {
      list.innerHTML = `<li class="empty-state">${data.detail || "Failed to load transactions"}</li>`;
      return;
    }

    if (!Array.isArray(data) || data.length === 0) {
      list.innerHTML = '<li class="empty-state">No transactions yet — pay someone from the Home tab.</li>';
      return;
    }

    data.forEach(tx => {
      const li = document.createElement("li");
      li.className = "tx-item";
      li.onclick = () => showTimeline(tx.id);

      const avatar = document.createElement("div");
      avatar.className = "tx-avatar";
      avatar.innerText = (tx.payee_name || tx.payee_vpa || "?").charAt(0).toUpperCase();

      const main = document.createElement("div");
      main.className = "tx-main";
      const to = document.createElement("div");
      to.className = "to";
      to.innerText = tx.payee_name || tx.payee_vpa || "Unknown payee";
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.innerText = `${labelFor(tx.status)} · ${tx.risk ?? 0}% risk`;
      main.appendChild(to);
      main.appendChild(meta);

      const amountWrap = document.createElement("div");
      amountWrap.className = "tx-amount";
      const amt = document.createElement("div");
      amt.className = "amt";
      amt.innerText = `₹${tx.amount}`;
      const pill = document.createElement("span");
      pill.className = `pill ${pillClassFor(tx.status)}`;
      pill.innerText = labelFor(tx.status);
      amountWrap.appendChild(amt);
      amountWrap.appendChild(pill);

      li.appendChild(avatar);
      li.appendChild(main);
      li.appendChild(amountWrap);
      list.appendChild(li);
    });

  } catch (err) {
    console.error("Transaction fetch error:", err);
    list.innerHTML = '<li class="empty-state">Server error. Try again later.</li>';
  }
}

loadMyTransactions();
