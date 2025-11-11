const report_checkboxes = document.querySelectorAll('.select_report');
report_checkboxes.forEach(checkbox => {
    checkbox.checked = false;
});

const select_all_checkboxes = document.querySelectorAll('#select_all');
select_all_checkboxes.forEach(checkbox => {
    checkbox.checked = false;
});

const bulk_action_dropdown = document.getElementById('bulk_action');
if (bulk_action_dropdown) {
    bulk_action_dropdown.value = 'post_hide';
}

document.getElementById('select_all').addEventListener('change', function () {
    const checkboxes = document.querySelectorAll('.select_report');
    checkboxes.forEach(checkbox => checkbox.checked = this.checked);
});

document.getElementById('apply_action').addEventListener('click', async function () {
    const report_parent_ids = Array.from(document.querySelectorAll('.select_report:checked')).map(checkbox => checkbox.getAttribute('data-report-id'));
    if (!report_parent_ids.length) {
        alert('No reports selected!');
        return;
    }

    const csrf_token_element = document.getElementById('sct');
    if (!csrf_token_element || !csrf_token_element.value) {
        alert('No csrf token found on page!')
        return;
    }
    const csrf_token = csrf_token_element.value;

    const action_element = document.getElementById('bulk_action');
    if (!action_element || !action_element.value) {
        alert('Either action not found, or not selected');
        return;
    }
    const action = action_element.value;

    const response = await fetch(`/reports/bulk/${action}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            report_parent_ids: report_parent_ids,
            sct: csrf_token,
        })
    })

    if (!response.ok) {
        alert(response.status);
    }

    location.reload(); // reload after receiving response
});