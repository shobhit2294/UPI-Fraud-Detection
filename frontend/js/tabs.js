function switchTab(name) {
  document.querySelectorAll(".tab-panel").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

  const panel = document.getElementById("tab-" + name);
  const btn = document.getElementById("navbtn-" + name);

  if (panel) panel.classList.add("active");
  if (btn) btn.classList.add("active");
}

// default to Home on load
switchTab("home");

// populate greeting / profile fields from the logged-in session
(function populateIdentity() {
  const email = localStorage.getItem("email") || "";
  const name = email.split("@")[0] || "there";
  const initial = (name[0] || "U").toUpperCase();

  const greetingEl = document.getElementById("greetingName");
  const emailEl = document.getElementById("profileEmail");
  const avatarEl = document.getElementById("profileAvatar");

  if (greetingEl) greetingEl.innerText = name;
  if (emailEl) emailEl.innerText = email || "—";
  if (avatarEl) avatarEl.innerText = initial;
})();
