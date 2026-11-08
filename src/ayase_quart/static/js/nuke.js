let nuke_toggle = sessionStorage.getItem('nuke_toggle') === 'true';

function set_nuke_form_visibility(el) {
    el.style.display = nuke_toggle ? 'inline' : 'none';
    el.parentElement.style.marginBottom = nuke_toggle ? '4px' : '0';
}

function apply_nuke_mode() {
    doc_query_all('.nukethreadform').forEach(set_nuke_form_visibility);
    document.getElementById('nuke_toggle').textContent = nuke_toggle
        ? 'Leave Nuke Mode'
        : 'Go To Nuke Mode';
}

function toggle_nuke_mode() {
    nuke_toggle = !nuke_toggle;
    sessionStorage.setItem('nuke_toggle', nuke_toggle);
    apply_nuke_mode();
}

async function on_nuke_response(form, response) {
    let message = 'Nuke request failed.';
    try {
        message = (await response.json()).message;
    } catch {}

    alert(message);

    if (response.ok) {
        remove_nuked_post(form);
    }
}

function parse_nuke_action(action) {
    // /nuke/<board>/<num>
    const parts = new URL(action, window.location.origin).pathname.split('/');
    return {board: parts[2], num: parts[3]};
}

function get_nuke_target_element(form) {
    const parsed = parse_nuke_action(form.getAttribute('action'));
    const el = document.querySelector(
        '[data-board="' + parsed.board + '"][data-num="' + parsed.num + '"]'
    );
    if (el) {
        return el;
    }
    // catalog, which doesn't need board specified
    return document.getElementById(parsed.num);
}

function remove_nuked_post(form) {
    const el = get_nuke_target_element(form);
    if (el) {
        el.remove();
    } else {
        location.reload();
    }
}

async function on_nuke_form_submit(e) {
    e.preventDefault();

    const form = e.target;

    let response;
    try {
        response = await fetch(form.action, {method: 'POST', body: new FormData(form)});
    } catch {
        alert('Nuke request failed.');
        return;
    }

    await on_nuke_response(form, response);
}

function bind_nuke_form(form) {
    form.addEventListener('submit', on_nuke_form_submit);
}

function init_nuke_mode() {
    const nuke_toggle_el = document.getElementById('nuke_toggle');
    if (!nuke_toggle_el) {
        return;
    }
    nuke_toggle_el.addEventListener('click', toggle_nuke_mode);
    apply_nuke_mode();
    doc_query_all('.nukethreadform').forEach(bind_nuke_form);
}

init_nuke_mode();
