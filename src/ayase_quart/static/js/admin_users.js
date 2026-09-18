function is_checkbox_checked(checkbox) {
    return checkbox.checked;
}

function handle_select_all_click(event) {
    event.preventDefault();
    const checkboxes = document.querySelectorAll('input[name=permissions]');
    const allChecked = Array.from(checkboxes).every(is_checkbox_checked);
    for (const checkbox of checkboxes) {
        checkbox.checked = !allChecked;
    }
}

document.getElementById('select_all').addEventListener('click', handle_select_all_click);
