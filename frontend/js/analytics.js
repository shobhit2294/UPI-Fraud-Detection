async function loadAnalytics() {
  const res = await fetch(`${API_BASE}/analytics/daily`, {
    headers: {
      Authorization: "Bearer " + localStorage.getItem("token")
    }
  });

  if (!res.ok) return;
  const data = await res.json();

  const labels = data.map(d => d.date);
  const totals = data.map(d => d.total);
  const frauds = data.map(d => d.fraud);

  const ctx = document.getElementById("analyticsChart");
  if (!ctx) return;

  new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Total transactions",
          data: totals,
          borderColor: "#5B21B6",
          backgroundColor: "rgba(91,33,182,0.08)",
          borderWidth: 2,
          tension: 0.3,
          fill: true,
        },
        {
          label: "Flagged as fraud",
          data: frauds,
          borderColor: "#DC2626",
          backgroundColor: "rgba(220,38,38,0.08)",
          borderWidth: 2,
          tension: 0.3,
          fill: true,
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { font: { family: "Inter" } } }
      },
      scales: {
        x: { ticks: { font: { family: "JetBrains Mono", size: 10 } } },
        y: { ticks: { font: { family: "JetBrains Mono", size: 10 } } }
      }
    }
  });
}

loadAnalytics();
