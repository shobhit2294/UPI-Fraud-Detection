async function loadMyTransactions() {
  const res = await fetch("http://localhost:8000/transactions");
  const data = await res.json();

  let html = "<tr><th>ID</th><th>Amount</th><th>Status</th></tr>";

  data.forEach(t => {
    html += `
      <tr>
        <td>${t.transaction_id}</td>
        <td>${t.amount}</td>
        <td>${t.fraud ? "Fraud" : "Safe"}</td>
      </tr>
    `;
  });

  document.getElementById("table").innerHTML = html;
}
