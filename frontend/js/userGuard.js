const role = localStorage.getItem("role");

if (role !== "user") {
  alert("User access only");
  window.location.href = "../login.html";
}
