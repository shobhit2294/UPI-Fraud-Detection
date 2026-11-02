function switchConsoleView(name) {
  document.querySelectorAll(".console-view").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".console-nav-item").forEach(el => el.classList.remove("active"));

  const view = document.getElementById("cview-" + name);
  const nav = document.getElementById("cnav-" + name);

  if (view) view.classList.add("active");
  if (nav) nav.classList.add("active");
}

(function populateOwnerIdentity() {
  const email = localStorage.getItem("email") || "Owner";
  const emailEl = document.getElementById("ownerEmail");
  const avatarEl = document.getElementById("ownerAvatar");
  if (emailEl) emailEl.innerText = email;
  if (avatarEl) avatarEl.innerText = (email[0] || "A").toUpperCase();
})();
