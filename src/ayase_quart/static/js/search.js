const searchform = document.getElementById('searchform');

const DATE_STORAGE_KEY = 'aq_search_date';

const searchInfoBtn = document.getElementById('search-info');
const searchHelper = document.getElementById('search-helper');

const dropZone = document.getElementById('drop_zone');
const fileDrop = dropZone ? dropZone.closest('.file-drop') : null;

const mediaHashInput = document.getElementById('media_hash');
const media_hash_file_input = document.getElementById('media_hash_file_input');

function on_searchform_submit(event) {
    event.preventDefault();

    const checked_boards = doc_query_all('input[name="boards"]:checked');
    if (checked_boards.length === 0) {
        alert('Please select at least one board.');
        return;
    }

    const formData = new FormData(searchform);
    const params = new URLSearchParams();
    const boards = [];

    const operatorToBaseKey = {
        'tlop': 'tl',
        'clop': 'cl',
        'wop': 'width',
        'hop': 'height',
    };

    const datePrefixes = ['date_after_', 'date_before_'];

    for (const [key, value] of formData.entries()) {
        if (value === "") continue;
        if (key === 'capcode' && value === "any") continue;
        if (key === 'date_mode') continue;
        if (key === 'date_preset') continue;
        if (datePrefixes.some((prefix) => key.startsWith(prefix))) continue;

        if (operatorToBaseKey[key]) {
            const baseKeyValue = formData.get(operatorToBaseKey[key]);
            if (!baseKeyValue) continue;
        }

        if (key === "boards") {
            boards.push(value);
        } else {
            params.append(key, value);
        }
    }

    const mode_input = searchform.querySelector('input[name="date_mode"]:checked');
    const isRelative = Boolean(mode_input && mode_input.value === 'relative');

    let afterDate = null;
    let beforeDate = null;

    if (isRelative) {
        afterDate = compute_relative_date(searchform.querySelector('select[name="date_preset"]').value);
    } else {
        afterDate = searchform.querySelector('input[name="date_after_date"]').value || null;
        beforeDate = searchform.querySelector('input[name="date_before_date"]').value || null;

        if (afterDate && afterDate > format_date(new Date())) {
            alert('Start date is in the future. No posts can match.');
            return;
        }

        if (afterDate && beforeDate && beforeDate < afterDate) {
            alert('Start date must be before the end date.');
            return;
        }
    }

    if (afterDate !== null) {
        params.append('date_after', afterDate);
    }

    if (beforeDate !== null) {
        params.append('date_before', beforeDate);
    }

    if (afterDate !== null || beforeDate !== null) {
        save_date_storage(isRelative ? {
            mode: 'relative',
            preset: searchform.querySelector('select[name="date_preset"]').value,
        } : {
            mode: 'absolute',
            after_date: searchform.querySelector('input[name="date_after_date"]').value,
            before_date: searchform.querySelector('input[name="date_before_date"]').value,
        });
    }

    let query = '';
    if (boards.length > 0) {
        query += `boards=${boards.join(',')}`;
    }

    const rest = params.toString();
    if (rest) {
        if (query) query += '&';
        query += rest;
    }

    const url = `${window.location.pathname}?${query}`;
    window.location.href = url;
}

function on_document_keydown(e) {
    if (e.key === 'Escape') {
        close_dropdowns();
    }
}

function close_dropdowns() {
    for (const drop of doc_query_all('.dropdown')) {
        const btn = drop.querySelector('.dropdown-btn');
        const menu = drop.querySelector('.dropdown-menu');
        btn.setAttribute('aria-expanded', 'false');
        menu.classList.add('hidden');
    }
}

function on_dropdown_btn_click(e) {
    const btn = e.target.closest('.dropdown-btn');
    if (!btn) return;

    const expanded = btn.getAttribute('aria-expanded') === 'true';
    close_dropdowns();
    if (!expanded) {
        btn.setAttribute('aria-expanded', 'true');
        btn.closest('.dropdown').querySelector('.dropdown-menu').classList.remove('hidden');
    }
}

function sync_dropdown(select) {
    const drop = select.closest('.dropdown');
    if (!drop) return;
    const btn = drop.querySelector('.dropdown-btn');
    const value = select.value;

    btn.classList.toggle('dropdown-muted', value === 'any' || value === '');

    for (const option of drop.querySelectorAll('.dropdown-option')) {
        const active = option.dataset.value === value;
        option.classList.toggle('active', active);
        option.setAttribute('aria-selected', active ? 'true' : 'false');
        if (active) btn.querySelector('.dropdown-value').textContent = option.textContent.trim();
    }
}

function on_dropdown_option_click(e) {
    const opt = e.target.closest('.dropdown-option');
    if (!opt) return;

    const drop = opt.closest('.dropdown');
    const select = drop.querySelector('select');

    select.value = opt.dataset.value;
    sync_dropdown(select);
    close_dropdowns();
}

function on_document_click_dropdown(e) {
    if (e.target.closest('.dropdown')) return;
    close_dropdowns();
}

function on_search_info_btn_click(e) {
    e.stopPropagation();
    const visible = !searchHelper.classList.contains('hidden');
    searchHelper.classList.toggle('hidden', visible);
    searchInfoBtn.classList.toggle('active', !visible);
    searchInfoBtn.setAttribute('aria-expanded', visible ? 'false' : 'true');
}

function on_drop_zone_dragover(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    fileDrop.classList.add('dragover');
}

function on_drop_zone_dragleave(e) {
    e.preventDefault();
    fileDrop.classList.remove('dragover');
}

function on_drop_zone_drop(e) {
    e.preventDefault();
    fileDrop.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
        generateMediaHash(file);
    }
}

function on_hash_file_input_change() {
    const file = media_hash_file_input.files[0];
    if (file) {
        generateMediaHash(file);
    }
}

function on_media_hash_loadend(e) {
    if (e.target.readyState === FileReader.DONE) {
        const fileContents = e.target.result;
        const digestBytes = Crypto.MD5(Crypto.charenc.Binary.stringToBytes(fileContents), {
            asBytes: true
        });
        const digestBase64 = Crypto.util.bytesToBase64(digestBytes);
        mediaHashInput.value = digestBase64;
    }
}

function generateMediaHash(file) {
    const reader = new FileReader();
    reader.onloadend = on_media_hash_loadend;
    reader.readAsBinaryString(file);
}

function refresh_tri_toggle(toggle, false_input, true_input) {
    for (const btn of get_data_elem_all(toggle, 'state')) {
        const state = btn.dataset.state;
        const active =
            (state === 'false' && false_input.checked) ||
            (state === 'true' && true_input.checked) ||
            (state === 'any' && !false_input.checked && !true_input.checked);
        btn.classList.toggle('active', active);
    }
}

function on_tri_option_click(e) {
    const btn = e.target.closest('.tri-option');
    if (!btn) return;

    const toggle = btn.closest('.tri-toggle');
    if (!toggle || !toggle.dataset.false || !toggle.dataset.true) return;

    const false_input = toggle.querySelector(`input[name="${toggle.dataset.false}"]`);
    const true_input = toggle.querySelector(`input[name="${toggle.dataset.true}"]`);

    const state = btn.dataset.state;
    false_input.checked = state === 'false';
    true_input.checked = state === 'true';
    refresh_tri_toggle(toggle, false_input, true_input);
}

function refresh_binary_toggle(group) {
    const name = group.dataset.name;
    const control = group.dataset.control;
    let input = null;

    if (control === 'bool') {
        input = group.closest('.binary-toggle').querySelector(`input[name="${name}"]`);
    } else {
        input = document.querySelector(`input[name="${name}"]:checked`);
    }

    for (const btn of get_data_elem_all(group, 'value')) {
        const btnValue = btn.dataset.value;
        let active;
        if (control === 'bool') {
            active = (btnValue === 'on') === Boolean(input && input.checked);
        } else if (input) {
            active = input.value === btnValue;
        } else {
            active = btn.dataset.default === '1';
        }
        btn.classList.toggle('active', active);
    }
}

function on_binary_toggle_click(e) {
    const btn = e.target.closest('.binary-option');
    if (!btn) return;

    const group = btn.closest('.toggle-group');
    if (!group || !group.dataset.name) return;

    const name = group.dataset.name;
    const control = group.dataset.control;

    if (control === 'bool') {
        const input = group.closest('.binary-toggle').querySelector(`input[name="${name}"]`);
        input.checked = btn.dataset.value === 'on';
    } else {
        const input = document.querySelector(`input[name="${name}"][value="${btn.dataset.value}"]`);
        if (input) input.checked = true;
    }

    refresh_binary_toggle(group);
}

function on_panel_number_keydown(e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key.length > 1) return;
    if (!/[0-9]/.test(e.key)) {
        e.preventDefault();
    }
}

function on_date_input() {
    this.classList.toggle('date-empty', !this.value);
}

function format_date(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function compute_relative_date(preset) {
    const now = new Date();

    const hours = { '1h': 1, '4h': 4 }[preset];
    if (hours !== undefined) {
        return Math.floor(now.getTime() / 1000) - hours * 3600;
    }

    if (preset === 'ytd') {
        return format_date(new Date(now.getFullYear(), 0, 1));
    }

    const days = { '1d': 1, '2d': 2, '7d': 7 }[preset];
    const months = { '1m': 1, '3m': 3, '6m': 6 }[preset];

    if (days === undefined && months === undefined) return null;

    const after = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (days !== undefined) {
        after.setDate(after.getDate() - days);
    } else {
        after.setMonth(after.getMonth() - months);
    }

    return format_date(after);
}

function toggle_date_branch(mode) {
    for (const el of doc_query_all('#searchform .date-branch-absolute')) {
        el.classList.toggle('hidden', mode !== 'absolute');
    }
    for (const el of doc_query_all('#searchform .date-branch-relative')) {
        el.classList.toggle('hidden', mode !== 'relative');
    }
}

function on_date_mode_click(e) {
    const btn = e.target.closest('.binary-option');
    if (!btn) return;
    const group = btn.closest('.toggle-group');
    if (!group || group.dataset.name !== 'date_mode') return;
    toggle_date_branch(btn.dataset.value);
}

function get_date_storage() {
    try {
        return JSON.parse(localStorage.getItem(DATE_STORAGE_KEY)) || {};
    } catch (e) {
        return {};
    }
}

function save_date_storage(state) {
    localStorage.setItem(DATE_STORAGE_KEY, JSON.stringify(state));
}

function clear_date_storage() {
    localStorage.removeItem(DATE_STORAGE_KEY);
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function restore_date_fields() {
    const sp = new URLSearchParams(window.location.search);
    const stored = get_date_storage();
    const mode_group = searchform.querySelector('.toggle-group[data-name="date_mode"]');

    const set_mode = (mode) => {
        searchform.querySelector(`input[name="date_mode"][value="${mode}"]`).checked = true;
        if (mode_group) refresh_binary_toggle(mode_group);
    };

    // no dates in the query string -> reset to the empty absolute default
    if (!sp.get('date_after') && !sp.get('date_before')) {
        clear_date_storage();
        set_mode('absolute');
        toggle_date_branch('absolute');
        return;
    }

    // after a search, local storage decides which toggle to display
    if (stored.mode === 'relative' && stored.preset) {
        set_mode('relative');

        const presetSelect = searchform.querySelector('select[name="date_preset"]');
        presetSelect.value = stored.preset;
        sync_dropdown(presetSelect);

        toggle_date_branch('relative');
        return;
    }

    // absolute (stored state, or a direct/shared visit when there is no storage):
    // stored dates win, URL values are the fallback. legacy unix ts links are converted
    for (const side of ['after', 'before']) {
        const dateInput = searchform.querySelector(`input[name="date_${side}_date"]`);
        const urlValue = sp.get(`date_${side}`);

        if (stored[`${side}_date`]) {
            dateInput.value = stored[`${side}_date`];
        } else if (urlValue) {
            if (DATE_RE.test(urlValue)) {
                dateInput.value = urlValue;
            } else {
                const ts = parseInt(urlValue, 10);
                if (!isNaN(ts) && ts > 0) {
                    dateInput.value = format_date(new Date(ts * 1000));
                }
            }
        }

        if (dateInput.value) dateInput.classList.remove('date-empty');
    }
    set_mode('absolute');
    toggle_date_branch('absolute');
}

function on_panel_number_paste(e) {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text') || '';
    const digits = text.replace(/\D/g, '');
    const el = e.target;
    const start = el.selectionStart || 0;
    const end = el.selectionEnd || start;
    el.value = el.value.slice(0, start) + digits + el.value.slice(end);
}

function auto_select_single_board() {
    const board_inputs = doc_query_all('#searchform input[name="boards"]');
    if (board_inputs.length !== 1) return;
    board_inputs[0].checked = true; // checked works with checkbox & radio inputs
}

function scroll_to_results() {
    const results = document.getElementById('resulttop');
    if (results && results.querySelector('.board, .gallery-grid')) {
        results.scrollIntoView({ block: 'start' });
    }
}

function init_search() {
    scroll_to_results();
    auto_select_single_board();

    for (const toggle of doc_query_all('#searchform .tri-toggle')) {
        if (!toggle.dataset.false || !toggle.dataset.true) continue;
        const false_input = toggle.querySelector(`input[name="${toggle.dataset.false}"]`);
        const true_input = toggle.querySelector(`input[name="${toggle.dataset.true}"]`);
        refresh_tri_toggle(toggle, false_input, true_input);
    }

    for (const group of doc_query_all('#searchform .binary-toggle .toggle-group')) {
        refresh_binary_toggle(group);
    }

    restore_date_fields();
}

if (searchform) {
    searchform.addEventListener('submit', on_searchform_submit);
    document.addEventListener('click', on_tri_option_click);
    document.addEventListener('click', on_binary_toggle_click);
    document.addEventListener('click', on_date_mode_click);
    document.addEventListener('click', on_dropdown_btn_click);
    document.addEventListener('click', on_dropdown_option_click);
    document.addEventListener('click', on_document_click_dropdown);

    const number_inputs = doc_query_all('#searchform input[type="number"]');
    for (const input of number_inputs) {
        input.addEventListener('keydown', on_panel_number_keydown);
        input.addEventListener('paste', on_panel_number_paste);
    }

    const date_inputs = doc_query_all('#searchform input[type="date"]');
    for (const input of date_inputs) {
        input.classList.toggle('date-empty', !input.value);
        input.addEventListener('input', on_date_input);
    }

    document.addEventListener('keydown', on_document_keydown);
}

if (fileDrop && mediaHashInput && media_hash_file_input) {
    fileDrop.addEventListener('dragover', on_drop_zone_dragover);
    fileDrop.addEventListener('dragleave', on_drop_zone_dragleave);
    fileDrop.addEventListener('drop', on_drop_zone_drop);
    media_hash_file_input.addEventListener('change', on_hash_file_input_change);
}

if (searchInfoBtn && searchHelper) {
    searchInfoBtn.addEventListener('click', on_search_info_btn_click);
}

/*
 * Crypto-JS v2.5.3
 * http://code.google.com/p/crypto-js/
 * (c) 2009-2012 by Jeff Mott. All rights reserved.
 * http://code.google.com/p/crypto-js/wiki/License
 */
(typeof Crypto=="undefined"||!Crypto.util)&&function(){var m=window.Crypto={},o=m.util={rotl:function(h,g){return h<<g|h>>>32-g},rotr:function(h,g){return h<<32-g|h>>>g},endian:function(h){if(h.constructor==Number)return o.rotl(h,8)&16711935|o.rotl(h,24)&4278255360;for(var g=0;g<h.length;g++)h[g]=o.endian(h[g]);return h},randomBytes:function(h){for(var g=[];h>0;h--)g.push(Math.floor(Math.random()*256));return g},bytesToWords:function(h){for(var g=[],i=0,a=0;i<h.length;i++,a+=8)g[a>>>5]|=(h[i]&255)<<
24-a%32;return g},wordsToBytes:function(h){for(var g=[],i=0;i<h.length*32;i+=8)g.push(h[i>>>5]>>>24-i%32&255);return g},bytesToHex:function(h){for(var g=[],i=0;i<h.length;i++)g.push((h[i]>>>4).toString(16)),g.push((h[i]&15).toString(16));return g.join("")},hexToBytes:function(h){for(var g=[],i=0;i<h.length;i+=2)g.push(parseInt(h.substr(i,2),16));return g},bytesToBase64:function(h){if(typeof btoa=="function")return btoa(n.bytesToString(h));for(var g=[],i=0;i<h.length;i+=3)for(var a=h[i]<<16|h[i+1]<<
8|h[i+2],b=0;b<4;b++)i*8+b*6<=h.length*8?g.push("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charAt(a>>>6*(3-b)&63)):g.push("=");return g.join("")},base64ToBytes:function(h){if(typeof atob=="function")return n.stringToBytes(atob(h));for(var h=h.replace(/[^A-Z0-9+\/]/ig,""),g=[],i=0,a=0;i<h.length;a=++i%4)a!=0&&g.push(("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".indexOf(h.charAt(i-1))&Math.pow(2,-2*a+8)-1)<<a*2|"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".indexOf(h.charAt(i))>>>
6-a*2);return g}},m=m.charenc={};m.UTF8={stringToBytes:function(h){return n.stringToBytes(unescape(encodeURIComponent(h)))},bytesToString:function(h){return decodeURIComponent(escape(n.bytesToString(h)))}};var n=m.Binary={stringToBytes:function(h){for(var g=[],i=0;i<h.length;i++)g.push(h.charCodeAt(i)&255);return g},bytesToString:function(h){for(var g=[],i=0;i<h.length;i++)g.push(String.fromCharCode(h[i]));return g.join("")}}}();
(function(){var m=Crypto,o=m.util,n=m.charenc,h=n.UTF8,g=n.Binary,i=m.MD5=function(a,b){var h=o.wordsToBytes(i._md5(a));return b&&b.asBytes?h:b&&b.asString?g.bytesToString(h):o.bytesToHex(h)};i._md5=function(a){a.constructor==String&&(a=h.stringToBytes(a));for(var b=o.bytesToWords(a),g=a.length*8,a=1732584193,d=-271733879,e=-1732584194,c=271733878,f=0;f<b.length;f++)b[f]=(b[f]<<8|b[f]>>>24)&16711935|(b[f]<<24|b[f]>>>8)&4278255360;b[g>>>5]|=128<<g%32;b[(g+64>>>9<<4)+14]=g;for(var g=i._ff,j=i._gg,k=
i._hh,l=i._ii,f=0;f<b.length;f+=16)var m=a,n=d,p=e,q=c,a=g(a,d,e,c,b[f+0],7,-680876936),c=g(c,a,d,e,b[f+1],12,-389564586),e=g(e,c,a,d,b[f+2],17,606105819),d=g(d,e,c,a,b[f+3],22,-1044525330),a=g(a,d,e,c,b[f+4],7,-176418897),c=g(c,a,d,e,b[f+5],12,1200080426),e=g(e,c,a,d,b[f+6],17,-1473231341),d=g(d,e,c,a,b[f+7],22,-45705983),a=g(a,d,e,c,b[f+8],7,1770035416),c=g(c,a,d,e,b[f+9],12,-1958414417),e=g(e,c,a,d,b[f+10],17,-42063),d=g(d,e,c,a,b[f+11],22,-1990404162),a=g(a,d,e,c,b[f+12],7,1804603682),c=g(c,a,
d,e,b[f+13],12,-40341101),e=g(e,c,a,d,b[f+14],17,-1502002290),d=g(d,e,c,a,b[f+15],22,1236535329),a=j(a,d,e,c,b[f+1],5,-165796510),c=j(c,a,d,e,b[f+6],9,-1069501632),e=j(e,c,a,d,b[f+11],14,643717713),d=j(d,e,c,a,b[f+0],20,-373897302),a=j(a,d,e,c,b[f+5],5,-701558691),c=j(c,a,d,e,b[f+10],9,38016083),e=j(e,c,a,d,b[f+15],14,-660478335),d=j(d,e,c,a,b[f+4],20,-405537848),a=j(a,d,e,c,b[f+9],5,568446438),c=j(c,a,d,e,b[f+14],9,-1019803690),e=j(e,c,a,d,b[f+3],14,-187363961),d=j(d,e,c,a,b[f+8],20,1163531501),
a=j(a,d,e,c,b[f+13],5,-1444681467),c=j(c,a,d,e,b[f+2],9,-51403784),e=j(e,c,a,d,b[f+7],14,1735328473),d=j(d,e,c,a,b[f+12],20,-1926607734),a=k(a,d,e,c,b[f+5],4,-378558),c=k(c,a,d,e,b[f+8],11,-2022574463),e=k(e,c,a,d,b[f+11],16,1839030562),d=k(d,e,c,a,b[f+14],23,-35309556),a=k(a,d,e,c,b[f+1],4,-1530992060),c=k(c,a,d,e,b[f+4],11,1272893353),e=k(e,c,a,d,b[f+7],16,-155497632),d=k(d,e,c,a,b[f+10],23,-1094730640),a=k(a,d,e,c,b[f+13],4,681279174),c=k(c,a,d,e,b[f+0],11,-358537222),e=k(e,c,a,d,b[f+3],16,-722521979),
d=k(d,e,c,a,b[f+6],23,76029189),a=k(a,d,e,c,b[f+9],4,-640364487),c=k(c,a,d,e,b[f+12],11,-421815835),e=k(e,c,a,d,b[f+15],16,530742520),d=k(d,e,c,a,b[f+2],23,-995338651),a=l(a,d,e,c,b[f+0],6,-198630844),c=l(c,a,d,e,b[f+7],10,1126891415),e=l(e,c,a,d,b[f+14],15,-1416354905),d=l(d,e,c,a,b[f+5],21,-57434055),a=l(a,d,e,c,b[f+12],6,1700485571),c=l(c,a,d,e,b[f+3],10,-1894986606),e=l(e,c,a,d,b[f+10],15,-1051523),d=l(d,e,c,a,b[f+1],21,-2054922799),a=l(a,d,e,c,b[f+8],6,1873313359),c=l(c,a,d,e,b[f+15],10,-30611744),
e=l(e,c,a,d,b[f+6],15,-1560198380),d=l(d,e,c,a,b[f+13],21,1309151649),a=l(a,d,e,c,b[f+4],6,-145523070),c=l(c,a,d,e,b[f+11],10,-1120210379),e=l(e,c,a,d,b[f+2],15,718787259),d=l(d,e,c,a,b[f+9],21,-343485551),a=a+m>>>0,d=d+n>>>0,e=e+p>>>0,c=c+q>>>0;return o.endian([a,d,e,c])};i._ff=function(a,b,g,d,e,c,f){a=a+(b&g|~b&d)+(e>>>0)+f;return(a<<c|a>>>32-c)+b};i._gg=function(a,b,g,d,e,c,f){a=a+(b&d|g&~d)+(e>>>0)+f;return(a<<c|a>>>32-c)+b};i._hh=function(a,b,g,d,e,c,f){a=a+(b^g^d)+(e>>>0)+f;return(a<<c|a>>>
32-c)+b};i._ii=function(a,b,g,d,e,c,f){a=a+(g^(b|~d))+(e>>>0)+f;return(a<<c|a>>>32-c)+b};i._blocksize=16;i._digestsize=16})();


init_search();