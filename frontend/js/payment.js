// ---------------- STATE ----------------
let capturedLocation = null;   // { latitude, longitude } once the user grants permission
let verifiedPayee = null;      // last successful /payees/verify result
let pendingTransactionId = null;

// ---------------- GEOLOCATION (consent-based, browser-native prompt) ----------------
function requestLocation() {
  const statusEl = document.getElementById("locationStatus");

  if (!navigator.geolocation) {
    statusEl.textContent = "📍 Location: not supported by this browser";
    return;
  }

  statusEl.textContent = "📍 Requesting location permission…";

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      capturedLocation = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
      };
      statusEl.textContent = "📍 Location on — helping verify this device";
    },
    (err) => {
      capturedLocation = null;
      statusEl.textContent = "📍 Location off — payment still works, minus this signal";
      console.warn("Geolocation denied/unavailable:", err.message);
    },
    { enableHighAccuracy: false, timeout: 8000 }
  );
}

// ask for location as soon as the page loads, so it's ready by the time the user pays
requestLocation();

// ---------------- PAYEE VERIFICATION ----------------
async function verifyPayee() {
  const vpa = document.getElementById("payeeVpa").value.trim();
  const resultEl = document.getElementById("payeeResult");
  verifiedPayee = null;

  if (!vpa) {
    resultEl.className = "payee-result warn";
    resultEl.textContent = "Enter a VPA to verify.";
    return;
  }

  const token = localStorage.getItem("token");

  try {
    const res = await fetch(`${API_BASE}/payees/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      body: JSON.stringify({ vpa }),
    });

    const data = await res.json();

    if (data.is_dummy) {
      resultEl.className = "payee-result warn";
      resultEl.innerHTML = `<span>🚫</span><span>${data.warning || "This account looks suspicious."}</span>`;
      verifiedPayee = null;
      return;
    }

    if (data.found && data.is_verified) {
      resultEl.className = "payee-result ok";
      resultEl.innerHTML = `<span>✅</span><span><strong>${data.account_holder_name}</strong><br>${data.bank}</span>`;
      verifiedPayee = vpa;
    } else {
      resultEl.className = "payee-result warn";
      resultEl.innerHTML = `<span>⚠️</span><span>${data.warning || "Unverified payee. Proceed with caution."}</span>`;
      verifiedPayee = vpa; // allowed, just flagged — mirrors real apps letting you pay unverified VPAs with a warning
    }
  } catch (err) {
    resultEl.className = "payee-result warn";
    resultEl.textContent = "Could not verify payee. Server not reachable.";
  }
}

// ---------------- PAY ----------------
async function pay() {
  const token = localStorage.getItem("token");

  const payeeVpa = document.getElementById("payeeVpa").value.trim();
  const amount = Number(document.getElementById("amount").value);
  const balance = Number(document.getElementById("balance").value);
  const city = document.getElementById("city").value.trim();
  const device = document.getElementById("device").value;
  const type = document.getElementById("type").value;

  if (!payeeVpa) {
    alert("Enter and verify a payee VPA first");
    return;
  }
  if (!city) {
    alert("City is required");
    return;
  }
  if (isNaN(amount) || isNaN(balance)) {
    alert("Amount and Balance must be valid numbers");
    return;
  }
  if (amount <= 0 || balance <= 0) {
    alert("Amount and Balance must be greater than zero");
    return;
  }
  if (amount > balance) {
    alert("Insufficient balance");
    return;
  }

  const payload = {
    amount,
    balance,
    city,
    device,
    transaction_type: type,
    payee_vpa: payeeVpa,
    latitude: capturedLocation ? capturedLocation.latitude : null,
    longitude: capturedLocation ? capturedLocation.longitude : null,
  };

  const res = await fetch(`${API_BASE}/transactions/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + token,
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json();

  if (!res.ok) {
    alert(data.detail || "Transaction failed");
    return;
  }

  pendingTransactionId = data.id;

  if (data.otp_required) {
    openOtpModal(data.demo_otp_code);
    return;
  }

  showTimeline(data.id);

  if (typeof loadMyTransactions === "function") {
    loadMyTransactions();
  }
}

// ---------------- OTP STEP-UP ----------------
function openOtpModal(demoCode) {
  document.getElementById("otpModal").classList.add("visible");
  const hint = document.getElementById("demoOtpHint");
  hint.textContent = demoCode
    ? `DEMO MODE — your OTP is ${demoCode} (a real app would text this to your phone, never show it here)`
    : "";
  document.getElementById("otpInput").value = "";
  document.getElementById("otpInput").focus();
}

function closeOtpModal() {
  document.getElementById("otpModal").classList.remove("visible");
  pendingTransactionId = null;
}

async function submitOtp() {
  const code = document.getElementById("otpInput").value.trim();
  const token = localStorage.getItem("token");

  if (!code || !pendingTransactionId) return;

  const res = await fetch(`${API_BASE}/transactions/${pendingTransactionId}/verify-otp`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + token,
    },
    body: JSON.stringify({ code }),
  });

  const data = await res.json();

  if (!res.ok) {
    alert(data.detail || "OTP verification failed");
    return;
  }

  closeOtpModal();
  showTimeline(data.id);

  if (typeof loadMyTransactions === "function") {
    loadMyTransactions();
  }
}

// ---------------- LIVE TIMELINE (polls until settled/failed/stuck) ----------------
function showTimeline(transactionId) {
  switchTab("track");
  const emptyEl = document.getElementById("trackEmpty");
  if (emptyEl) emptyEl.style.display = "none";
  pollTimeline(transactionId);
}

const STAGE_ICON = {
  INITIATED: "🚀",
  OTP_REQUIRED: "🔐",
  OTP_VERIFIED: "🔓",
  BANK_ACK: "🏦",
  PSP_PROCESSING: "🔁",
  AGGREGATOR_PROCESSING: "🔀",
  SETTLED: "✅",
  FAILED: "❌",
  STUCK_PENDING_RECONCILIATION: "⏳",
};

async function pollTimeline(transactionId) {
  const token = localStorage.getItem("token");
  const statusEl = document.getElementById("timelineStatus");
  const listEl = document.getElementById("timelineList");

  const terminalStatuses = ["SETTLED", "FAILED", "STUCK_PENDING_RECONCILIATION"];

  const tick = async () => {
    try {
      const res = await fetch(`${API_BASE}/transactions/${transactionId}/timeline`, {
        headers: { Authorization: "Bearer " + token },
      });
      const events = await res.json();

      if (!Array.isArray(events)) return;

      listEl.innerHTML = "";
      events.forEach((e) => {
        const li = document.createElement("li");

        const dot = document.createElement("div");
        dot.className = "timeline-dot";

        const body = document.createElement("div");
        body.className = "timeline-body";

        const stage = document.createElement("div");
        stage.className = "stage";
        stage.innerText = `${STAGE_ICON[e.stage] || "•"} ${e.stage.replaceAll("_", " ")}`;

        const actor = document.createElement("div");
        actor.className = "actor";
        actor.innerText = e.actor;

        body.appendChild(stage);
        body.appendChild(actor);

        if (e.message) {
          const msg = document.createElement("div");
          msg.className = "msg";
          msg.innerText = e.message;
          body.appendChild(msg);
        }

        li.appendChild(dot);
        li.appendChild(body);
        listEl.appendChild(li);
      });

      const lastStage = events.length ? events[events.length - 1].stage : "PENDING";
      statusEl.innerText = lastStage.replaceAll("_", " ");

      if (!terminalStatuses.includes(lastStage)) {
        setTimeout(tick, 1500);
      }
    } catch (err) {
      console.error("Timeline poll error:", err);
    }
  };

  tick();
}
