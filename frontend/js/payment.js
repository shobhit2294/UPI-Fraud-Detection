async function makePayment() {
  const amount = document.getElementById("amount").value;

  const response = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      transaction_id: Date.now(),
      amount: Number(amount),
      device_type: "Android",
      location: "Delhi"
    })
  });

  const data = await response.json();

  if (data.fraud) {
    alert(`❌ FRAUD DETECTED\nRisk Score: ${data.risk_score}%`);
  } else {
    alert(`✅ PAYMENT SUCCESS\nRisk Score: ${data.risk_score}%`);
  }
}
