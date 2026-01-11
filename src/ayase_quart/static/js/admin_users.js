document.getElementById('select_all').addEventListener('click', function (e) {
    e.preventDefault();
    const checkboxes = document.querySelectorAll('input[name=permissions]');
    const allChecked = Array.from(checkboxes).every(checkbox => checkbox.checked);
    checkboxes.forEach(checkbox => checkbox.checked = !allChecked);
});