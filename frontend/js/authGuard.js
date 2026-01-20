
const role = localStorage.getItem("role");
const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "../login.html";
}


if (window.location.pathname.includes("owner") && role !== "owner") {
  alert("Unauthorized");
  window.location.href = "../login.html";
}
