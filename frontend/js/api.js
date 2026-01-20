async function apiFetch(url, options = {}) {
    const token = localStorage.getItem("token");

    const res = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        }
    });

    if (res.status === 401) {
        alert("Session expired");
        localStorage.clear();
        window.location.href = "../login.html";
        return;
    }

    return res.json();
}
