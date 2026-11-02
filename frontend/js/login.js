let otpRequested = false;

function normalizedPhone() {
  const value = document.getElementById("phone").value.trim();
  if (!value) throw new Error("Enter your mobile number first");
  return value;
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.textContent = busy ? "Please wait…" : label;
}

async function requestOtp() {
  const button = document.getElementById("send-otp-button");
  const message = document.getElementById("otp-message");
  try {
    setBusy(button, true, "Send OTP");
    const response = await fetch(`${API_BASE}/auth/request-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: normalizedPhone() })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not send OTP");

    otpRequested = true;
    document.getElementById("otp-area").hidden = false;
    document.getElementById("verify-otp-button").hidden = false;
    button.textContent = "Resend OTP";
    message.textContent = `${data.message} Expires in ${data.expires_in_seconds} seconds.`;
    // DEMO_MODE only: production responses must never expose the OTP.
    if (data.demo_otp) {
      document.getElementById("otp").value = data.demo_otp;
      message.textContent += " Demo OTP filled automatically.";
      document.getElementById("verify-otp-button").focus();
    } else {
      document.getElementById("otp").focus();
    }
  } catch (error) {
    message.textContent = error.message;
  } finally {
    if (button.disabled) setBusy(button, false, otpRequested ? "Resend OTP" : "Send OTP");
  }
}

async function verifyOtp() {
  const button = document.getElementById("verify-otp-button");
  const message = document.getElementById("otp-message");
  if (!otpRequested) return;
  try {
    setBusy(button, true, "Verify and continue");
    const response = await fetch(`${API_BASE}/auth/verify-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: normalizedPhone(), otp: document.getElementById("otp").value.trim() })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Invalid OTP");
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("role", data.role || "user");
    localStorage.setItem("phone", data.phone || normalizedPhone());
    window.location.href = data.role === "owner" ? "dashboard/owner.html" : "dashboard/user.html";
  } catch (error) {
    message.textContent = error.message;
    setBusy(button, false, "Verify and continue");
  }
}

document.getElementById("phone").addEventListener("keydown", (event) => {
  if (event.key === "Enter") requestOtp();
});

document.getElementById("otp").addEventListener("input", (event) => {
  event.target.value = event.target.value.replace(/\D/g, "").slice(0, 6);
  if (event.target.value.length === 6) verifyOtp();
});
