// Main JavaScript for Examination Management System

document.addEventListener('DOMContentLoaded', function () {
    // 1. Bootstrap Form Validation (Frontend Validation)
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // 2. Client-side Live Table Filter
    const searchInputs = document.querySelectorAll('[data-table-search]');
    searchInputs.forEach(input => {
        const targetTableId = input.getAttribute('data-table-search');
        const table = document.getElementById(targetTableId);
        if (!table) return;

        input.addEventListener('input', function () {
            const query = this.value.toLowerCase().trim();
            const rows = table.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });

    // 3. Confirm Delete Prompts
    const deleteForms = document.querySelectorAll('.confirm-action');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            const msg = form.getAttribute('data-confirm-message') || 'Are you sure you want to proceed with this action?';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
});

