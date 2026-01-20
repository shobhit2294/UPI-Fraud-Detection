async function simulateTransaction() {
    const amount = Math.floor(Math.random() * 10000);

    await apiFetch(
        `http://127.0.0.1:8000/transactions?amount=${amount}`,
        { method: "POST" }
    );
}

async function loadTransactions() {
    const data = await apiFetch("http://127.0.0.1:8000/transactions");

    const table = document.getElementById("txTable");
    table.innerHTML = "";

    data.forEach(tx => {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${tx.id}</td>
            <td>₹${tx.amount}</td>
            <td class="${tx.status}">${tx.status.toUpperCase()}</td>
            <td>${tx.risk}%</td>
        `;

        table.appendChild(row);
    });
}

async function loadAnalytics() {
    const data = await apiFetch("http://127.0.0.1:8000/analytics/daily");

    const ctx = document.getElementById("analyticsChart").getContext("2d");

    if (window.analyticsChart) {
        window.analyticsChart.destroy();
    }

    window.analyticsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.labels,
            datasets: [{
                label: "Transactions per day",
                data: data.counts
            }]
        }
    });
}

loadTransactions();
loadAnalytics();

// auto refresh every 2 seconds
setInterval(() => {
    loadTransactions();
    loadAnalytics();
}, 2000);
