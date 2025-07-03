// image hover display
function media_mouseout(event) {
    if (event.target.tagName.toLowerCase() === 'img') {
        removeClonedImages();
    }
}
const video_extensionss = new Set(['mp4', 'webm']);
function media_mouseover(event) {
    const img = event.target;
    const extension = img.getAttribute('data-ext');
    if (!extension || video_extensionss.has(extension)) return;
    if (img.getAttribute('data-expanded') === "true") return;
    if (!(img instanceof HTMLImageElement)) return;
    if (!img.hasAttribute('data-full_media_src') && !img.hasAttribute('data-thumb_src')) return;
    if (document.getElementById('img_cloned')) return;

    const img_cloned = document.createElement('img');
    img_cloned.id = 'img_cloned';
    img_cloned.classList.add('hover_image');
    img_cloned.src = img.getAttribute('data-full_media_src') || img.getAttribute('data-thumb_src');
    document.body.appendChild(img_cloned);
}

const media_containers = document.querySelectorAll('.media_cont');
for (const container of media_containers) {
    container.addEventListener('mouseover', media_mouseover);
    container.addEventListener('mouseout', media_mouseout);
}

function quoteline_mouseover(event) {
    const quotelink = event.target;
    const backlink = quotelink.parentElement.parentElement.id;

    const num = quotelink.getAttribute("href").split("#p")[1];
    const board_shortname = quotelink.getAttribute('data-board_shortname');
    let backlink_num = backlink ? backlink.replace(/^bl_/, '') : null;

    const id_post_num = "#p" + num;
    let target_post = document.querySelector(id_post_num);

    quotelink_preview_hide();

    if (target_post == null) {
        fetch(`/${board_shortname}/post/${num}`).then(response => {
            return response.ok ? response.json() : Promise.reject();
        }).then(data => {
            let previewContent = data && data.html_content ? data.html_content : get_quotelink_preview_default_string();
            target_post = document.createElement("div");
            target_post.innerHTML = previewContent;
            quotelink_preview_show(target_post, quotelink, backlink_num);
        }).catch(() => {
            let default_preview = document.createElement("div");
            default_preview.innerHTML = get_quotelink_preview_default_string();
            quotelink_preview_show(default_preview, quotelink, backlink_num);
        });
    } else {
        quotelink_preview_show(target_post, quotelink, backlink_num);
    }
}
const quotelinks = document.querySelectorAll("a.quotelink");
for (const quotelink of quotelinks) {
    quotelink.addEventListener("mouseover", quoteline_mouseover);
    quotelink.addEventListener("mouseleave", quotelink_preview_hide);
}

function get_quotelink_preview_default_string() {
    return `<div class="postContainer replyContainer"><div class="post reply">
    <div class="postInfo desktop"><span class="nameBlock"><span class="name">Ayase Quart</span></span></div>
    <blockquote class="postMessage">Could not find post.</blockquote>
    </div></div>`;
}

function quotelink_preview_hide() {
    for (const qp of document.querySelectorAll("#quote-preview")) {
        qp.remove();
    }
}

function quotelink_preview_show(target_post, quotelink, backlink_num) {
    let preview = target_post.cloneNode(true);
    preview.id = "quote-preview";

    // highlight the recipient of the reply to help when there are multiple quotelinks
    const board_shortname = quotelink.getAttribute("data-board_shortname");
    const recipients = preview.querySelectorAll(`a.quotelink`);
    for (const recipient of recipients) {
        const recipient_post_num = recipient.getAttribute("href").split("#p")[1];
        const recipient_board_shortname = recipient.getAttribute("data-board_shortname");

        if (recipient_post_num === backlink_num && recipient_board_shortname === board_shortname) {
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
    preview.style.border = "1px solid white";
    preview.style.backgroundColor = "#282a2e";
}

if (document.getElementById('vox')){
    const vox_button = document.createElement('button');
    vox_button.textContent = 'Load Thread Reader';
    const tools = document.getElementById('tools');
    const board = tools.getAttribute('data-board_shortname');
    const thread_num = tools.getAttribute('data-thread_num');
    tools.appendChild(vox_button);

    vox_button.addEventListener('click', () => {
        vox_button.remove();

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120_000);

        const url = `/${board}/thread/${thread_num}/vox`;
        fetch(url, { signal: controller.signal }).then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) {
                throw new Error('Response not ok.');
            }
            return response.blob();
        }).then(blob => {
            const audioUrl = URL.createObjectURL(blob);
            const audio = document.createElement('audio');
            audio.src = audioUrl;
            audio.controls = true;
            audio.autoplay = true;
            tools.appendChild(audio);
        }).catch(error => {
            console.error('Fetch error or timeout:', error);
            const errorMsg = document.createElement('p');
            errorMsg.textContent = 'Failed to load audio.';
            tools.appendChild(errorMsg);
        });
    });
}