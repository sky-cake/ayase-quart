let nuke_toggle = false;

function toggle_nuke_mode() {
    nuke_toggle = !nuke_toggle;
    doc_query_all('.nukethreadform').forEach(function(el) {
        el.style.display = nuke_toggle ? 'inline' : 'none';
    });
    document.getElementById('nuke_toggle').textContent = nuke_toggle
        ? 'Leave Nuke Mode'
        : 'Go To Nuke Mode';
}

document.getElementById('nuke_toggle').addEventListener('click', toggle_nuke_mode);
