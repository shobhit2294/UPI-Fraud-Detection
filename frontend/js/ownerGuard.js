const token = localStorage.getItem("token");
const role = localStorage.getItem("role");

if (!token) {
    window.location.href = "../login.html";
}

if (role !== "owner") {
    alert("Access denied");
    window.location.href = "../login.html";
}
