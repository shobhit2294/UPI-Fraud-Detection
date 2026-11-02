const role = localStorage.getItem("role");

if (role !== "owner") {
  alert("Owner access only");
  window.location.href = "../login.html";
}
