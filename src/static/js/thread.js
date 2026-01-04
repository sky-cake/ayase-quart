// image hover display
function media_mouseout(event) {
    if (event.target.tagName.toLowerCase() === 'img') {
        remove_overlay_image();
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
    const num = quotelink.getAttribute("href").split("#p")[1];
    const board = get_data_string(quotelink, 'board');

    const backlink = quotelink.parentElement.parentElement.id;
    const backlink_num = backlink ? backlink.replace(/^(bl_|p)/, '') : null;

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
            quotelink.href = `/${board}/thread/${data.thread_num}${id_post_num}`; // update off-page href with real thread_num
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

function init_thread() {
    setup_media_events();
    setup_quotelink_events();
}

init_thread();
