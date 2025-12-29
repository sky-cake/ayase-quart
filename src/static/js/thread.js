// image hover display
function media_mouseout(event) {
    if (event.target.tagName.toLowerCase() === 'img') {
        remove_cloned_image();
    }
}

function media_mouseover(event) {
    const img = event.target;
    const extension = get_data_string(img, 'ext')
    if (!extension || ext_is_video(extension)) return;
    if (get_data_string(img, 'expanded') === "true") return;
    if (!(img instanceof HTMLImageElement)) return;
    if (!img.hasAttribute('data-full_media_src') && !img.hasAttribute('data-thumb_src')) return;
    if (document.getElementById('img_cloned')) return;

    const img_cloned = document.createElement('img');
    img_cloned.id = 'img_cloned';
    img_cloned.classList.add('hover_image');
    img_cloned.src = img.getAttribute('data-full_media_src') || img.getAttribute('data-thumb_src');
    document.body.appendChild(img_cloned);
}

function setup_media_events() {
    const media_containers = doc_query_all('.media_cont');
    for (const container of media_containers) {
        container.addEventListener('mouseover', media_mouseover);
        container.addEventListener('mouseout', media_mouseout);
    }
}

const quotelink_resp_cache = new Map();
const quotelink_fetching = new Set();
function quotelink_mouseover(event) {
    const quotelink = event.target;
    const backlink = quotelink.parentElement.parentElement.id;

    const num = quotelink.getAttribute("href").split("#p")[1];
    const board = get_data_string(quotelink, 'board');
    let backlink_num = backlink ? backlink.replace(/^bl_/, '') : null;

    const id_post_num = "#p" + num;
    let target_post = document.querySelector(id_post_num);

    quotelink_preview_hide();

    if (target_post !== null) { // on-page post
        quotelink_preview_show(target_post, quotelink, backlink_num);
        return;
    }

    const post_key = `/${board}/post/${num}`;
    target_post = document.createElement("div");
    if (quotelink_resp_cache.has(post_key)) { // off-page post in cache
        target_post.innerHTML = quotelink_resp_cache.get(post_key);
        quotelink_preview_show(target_post, quotelink, backlink_num);
        return;
    }
    if (quotelink_fetching.has(post_key)) return; // already in flight

    quotelink_fetching.add(post_key)
    fetch(post_key).then(response => {
        return response.ok ? response.json() : Promise.reject();
    }).then(data => {
        let previewContent = data && data.html_content ? data.html_content : get_quotelink_preview_default_string();
        target_post.innerHTML = previewContent;
        if (data && data.html_content) { // only cache good results
            quotelink_resp_cache.set(post_key, data.html_content);
        }
    }).catch(() => {
        target_post.innerHTML = get_quotelink_preview_default_string();
    }).finally(() => {
        quotelink_preview_show(target_post, quotelink, backlink_num);
        quotelink_fetching.delete(post_key); // clear in flight
    });
}

function setup_quotelink_events() {
    const quotelinks = doc_query_all("a.quotelink");
    for (const quotelink of quotelinks) {
        quotelink.removeEventListener("mouseover", quotelink_mouseover);
        quotelink.removeEventListener("mouseleave", quotelink_preview_hide);
        quotelink.addEventListener("mouseover", quotelink_mouseover);
        quotelink.addEventListener("mouseleave", quotelink_preview_hide);
    }
}

function get_quotelink_preview_default_string() {
    return `<div class="postContainer replyContainer"><div class="post reply">
    <div class="postInfo desktop"><span class="nameBlock"><span class="name">Ayase Quart</span></span></div>
    <blockquote class="postMessage">Could not find post.</blockquote>
    </div></div>`;
}

function quotelink_preview_hide() {
    const qp = document.getElementById('quote-preview');
    if (qp) {
        qp.remove();
    }
}

function quotelink_preview_show(target_post, quotelink, backlink_num) {
    const existing = document.getElementById('quote-preview');
    if (existing) existing.remove();

    let preview = target_post.cloneNode(true);
    preview.id = "quote-preview";

    // highlight the recipient of the reply to help when there are multiple quotelinks
    const board = get_data_string(quotelink, 'board');
    const recipients = preview.querySelectorAll(`a.quotelink`);
    for (const recipient of recipients) {
        const recipient_post_num = recipient.getAttribute("href").split("#p")[1];
        const recipient_board = get_data_string(recipient, 'board');

        if (recipient_post_num === backlink_num && recipient_board === board) {
            recipient.classList.add("hl_dark");
            break;
        }
    }

    preview.addEventListener("mouseover", quotelink_preview_hide);

    document.body.appendChild(preview);

    const ql = quotelink.getBoundingClientRect();
    const prev = preview.getBoundingClientRect();
    const scroll_y = document.documentElement.scrollTop;

    let top = ql.bottom + scroll_y - prev.height / 2;
    let left = ql.right + 5;
    const space_right = window.innerWidth - ql.right;
    const space_left = ql.left;

    // If screen width is below 500px, center the popup
    if (window.innerWidth < 500) {
        left = (window.innerWidth - prev.width) / 2;
        top = ql.bottom + scroll_y + 12;
    } else {
        // Don't clip top
        if (top < scroll_y) {
            top = scroll_y + 5;
        }
        // If there's less than 400px on the right, try putting it on the left
        if (space_right < 400) {
            left = ql.left - prev.width - 5;
        }
        // If it goes off the left side, center it instead
        if (left < 0) {
            left = (window.innerWidth - prev.width) / 2;
            top = ql.bottom + scroll_y + 12;
        }
        // Adjust width to prevent clipping on the right
        if (left + prev.width > window.innerWidth) {
            preview.style.width = `${window.innerWidth - left - 20}px`;
        }
    }
    preview.style.top = `${top}px`;
    preview.style.left = `${left}px`;
    preview.style.border = "1px solid #686868ff";
    preview.style.backgroundColor = "#282a2e";
}

function gallery_view() {
    const btn_class = 'form_btn pbtn';

    const gallery_control_cont = document.createElement('div');
    gallery_control_cont.classList = 'm-1'
    document.getElementById('board_nav').insertAdjacentElement('afterend', gallery_control_cont);

    const state = {
        current_page: 0,
        page_size: 25,
        media_nodes: [],
        file_nodes: [],
        is_gallery_mode: false
    };

    const prev_btn = document.createElement('button');
    prev_btn.className = btn_class;
    prev_btn.textContent = '« Prev';
    prev_btn.disabled = true;
    prev_btn.onclick = () => {
        if (state.current_page > 0) {
            state.current_page--;
            open_page();
        }
    };

    const next_btn = document.createElement('button');
    next_btn.className = btn_class;
    next_btn.textContent = 'Next »';
    next_btn.disabled = true;
    next_btn.onclick = () => {
        const max_page = Math.floor((state.media_nodes.length - 1) / state.page_size);
        if (state.current_page < max_page) {
            state.current_page++;
            open_page();
        }
    };

    const toggle_btn = document.createElement('button');
    toggle_btn.className = btn_class + ' block';
    toggle_btn.textContent = 'Gallery';
    toggle_btn.onclick = () => {
        if (state.is_gallery_mode) {
            revert();
            state.is_gallery_mode = false;
            toggle_btn.textContent = 'Gallery';
            prev_btn.style.display = 'none';
            next_btn.style.display = 'none';
            per_page_select.style.display = 'none';
            page_list_div.innerHTML = '';
        } else {
            state.current_page = 0;
            open_page();
            state.is_gallery_mode = true;
            toggle_btn.textContent = 'Revert';
            prev_btn.style.display = '';
            next_btn.style.display = '';
            per_page_select.style.display = '';
        }
    };

    const per_page_select = document.createElement('select');
    per_page_select.className = btn_class;
    for (let i = 10; i <= 50; i += 10) {
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = i;
        per_page_select.appendChild(opt);
    }
    per_page_select.value = 20;
    per_page_select.onchange = () => {
        state.page_size = parseInt(per_page_select.value);
        state.current_page = 0;
        if (state.is_gallery_mode) open_page();
    };
    per_page_select.style.display = 'none';

    const page_list_div = document.createElement('div');

    function create_controls() {
        if (!gallery_control_cont) return;
        gallery_control_cont.appendChild(toggle_btn);
        gallery_control_cont.appendChild(per_page_select);
        gallery_control_cont.appendChild(prev_btn);
        gallery_control_cont.appendChild(next_btn);
        gallery_control_cont.appendChild(page_list_div);
        prev_btn.style.display = 'none';
        next_btn.style.display = 'none';
        per_page_select.style.display = 'none';
    }

    function open_page() {
        if (!state.media_nodes.length) {
            state.media_nodes = Array.from(doc_query_all('.media_cont'));
            state.file_nodes = Array.from(doc_query_all('.file'));
        }
        if (!state.media_nodes.length || !state.file_nodes.length) return;

        const board = document.querySelector('div.board');
        let gallery_div = document.querySelector('.gallery');
        if (!gallery_div) {
            gallery_div = document.createElement('div');
            gallery_div.className = 'gallery';
            board.insertBefore(gallery_div, board.firstChild);
        } else {
            gallery_div.innerHTML = '';
        }

        const start = state.current_page * state.page_size;
        const end = Math.min(start + state.page_size, state.media_nodes.length);

        for (let i = start; i < end; i++) {
            const node = state.media_nodes[i];
            node.style.display = 'inline-block';
            gallery_div.appendChild(node);
        }

        update_buttons();
        update_page_info();
    }

    function update_buttons() {
        prev_btn.disabled = state.current_page === 0;
        const max_page = Math.floor((state.media_nodes.length - 1) / state.page_size);
        next_btn.disabled = state.current_page >= max_page;
    }

    function set_up_gallery_buttons() {
        const buttons = doc_query_all('.gallery_page_btn');
        for (const btn of buttons) {
            btn.addEventListener('click', () => {
                window._gotoGalleryPage(parseInt(btn.dataset.page));
            });
        }
    }

    function update_page_info() {
        const total_pages = Math.ceil(state.media_nodes.length / state.page_size);
        let html = '<div>';

        for (let i = 0; i < total_pages; i++) {
            if (i === state.current_page) {
                html += `<button class="${btn_class} hl_magenta">${i + 1}</button>`;
            } else {
                html += `<button class="${btn_class} gallery_page_btn" data-page="${i}">${i + 1}</button>`;
            }
        }
        page_list_div.innerHTML = html + '</div>';
        set_up_gallery_buttons();
    }

    window._gotoGalleryPage = (page) => {
        state.current_page = page;
        open_page();
    };

    function revert() {
        if (!state.media_nodes.length || !state.file_nodes.length) return;
        for (let i = 0; i < state.media_nodes.length; i++) {
            const node = state.media_nodes[i];
            const file = state.file_nodes[i];
            file.appendChild(node);
            node.style.display = '';
        }
        const gallery_div = document.querySelector('.gallery');
        if (gallery_div) gallery_div.remove();
        prev_btn.disabled = true;
        next_btn.disabled = true;
    }

    create_controls();
}

function init_thread() {
    setup_media_events();
    setup_quotelink_events();

    if (document.getElementById('tools') && document.getElementById('board_nav')){
        gallery_view();
    }
}

init_thread();
