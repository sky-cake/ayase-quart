const report_checkboxes = document.querySelectorAll('.select_report');
report_checkboxes.forEach(uncheck_checkbox);

const select_all_checkboxes = document.querySelectorAll('#select_all');
select_all_checkboxes.forEach(uncheck_checkbox);

const bulk_action_dropdown = document.getElementById('bulk_action');
if (bulk_action_dropdown) {
    bulk_action_dropdown.value = 'post_hide';
}

function uncheck_checkbox(checkbox) {
    checkbox.checked = false;
}

function get_report_parent_id(checkbox) {
    return checkbox.getAttribute('data-report-id');
}

function handle_select_all_change() {
    const checkboxes = document.querySelectorAll('.select_report');
    for (const checkbox of checkboxes) {
        checkbox.checked = this.checked;
    }
}

async function apply_bulk_action() {
    const report_parent_ids = Array.from(document.querySelectorAll('.select_report:checked')).map(get_report_parent_id);
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
}

document.getElementById('select_all').addEventListener('change', handle_select_all_change);

document.getElementById('apply_action').addEventListener('click', apply_bulk_action);
