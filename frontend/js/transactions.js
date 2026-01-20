async function loadTransactions() {
  const res = await fetch(`${API_BASE}/transactions`);
  const data = await res.json();

  const table = document.getElementById("transactions");

  table.innerHTML = "";

  data.forEach(tx => {
    const row = `
      <tr>
        <td>${tx.transaction_id}</td>
        <td>${tx.amount}</td>
        <td>${tx.device_type}</td>
        <td>${tx.location}</td>
        <td>${tx.fraud ? "❌ Fraud" : "✅ Safe"}</td>
        <td>${tx.risk_score}%</td>
        <td>${tx.created_at}</td>
      </tr>
    `;
    table.innerHTML += row;
  });
}

loadTransactions();
