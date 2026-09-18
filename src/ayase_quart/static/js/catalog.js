let nuke_toggle = false;

function set_nuke_form_visibility(el) {
    el.style.display = nuke_toggle ? 'inline' : 'none';
    el.parentElement.style.marginBottom = nuke_toggle ? '4px' : '0';
}

function toggle_nuke_mode() {
    nuke_toggle = !nuke_toggle;
    doc_query_all('.nukethreadform').forEach(set_nuke_form_visibility);
    document.getElementById('nuke_toggle').textContent = nuke_toggle
        ? 'Leave Nuke Mode'
        : 'Go To Nuke Mode';
}

document.getElementById('nuke_toggle').addEventListener('click', toggle_nuke_mode);
