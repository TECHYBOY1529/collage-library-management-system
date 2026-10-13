document.addEventListener("DOMContentLoaded", function () {
    // Confirmation dialogs for destructive or critical actions
    const confirmForms = document.querySelectorAll("form[data-confirm]");
    confirmForms.forEach(function (form) {
        form.addEventListener("submit", function (e) {
            const msg = form.getAttribute("data-confirm") || "Are you sure you want to proceed?";
            if (!window.confirm(msg)) {
                e.preventDefault();
            }
        });
    });

    // Client-side quick table search filter
    const tableSearchInputs = document.querySelectorAll("[data-table-filter]");
    tableSearchInputs.forEach(function (input) {
        const targetSelector = input.getAttribute("data-table-filter");
        const table = document.querySelector(targetSelector);
        if (!table) return;

        input.addEventListener("input", function () {
            const query = input.value.toLowerCase().trim();
            const rows = table.querySelectorAll("tbody tr");
            rows.forEach(function (row) {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(query) ? "" : "none";
            });
        });
    });
});
