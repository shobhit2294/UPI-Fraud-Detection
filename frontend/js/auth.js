async function login() {
    const phone = document.getElementById("phone").value;
    const password = document.getElementById("password").value;

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ phone, password })
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail || "Login failed");
            return;
        }

        // ✅ SAVE TOKEN + ROLE
        localStorage.setItem("token", data.token);
        localStorage.setItem("role", data.role);

        // ✅ REDIRECT
        if (data.role === "owner") {
            window.location.href = "dashboard/owner.html";
        } else {
            window.location.href = "dashboard/user.html";
        }

    } catch (err) {
        alert("Server not reachable");
    }
}
