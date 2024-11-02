// image hover display
document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll('img').forEach(img => {
        img.addEventListener('mouseover', function () {
            const img_cloned = document.createElement('img');
            img_cloned.id = 'img_cloned';

            const full_media_src = this.getAttribute('data-full_media_src');
            const thumb_src = this.getAttribute('data-thumb_src');

            var src = '';
            if (full_media_src){
                src = full_media_src;
            }
            else if (thumb_src) {
                src = thumb_src;
            }

            if (src != ''){
                img_cloned.src = full_media_src;
                img_cloned.classList.add('hover_image');

                img_cloned.classList.add('hover_image');
                document.body.appendChild(img_cloned);

                img.addEventListener('mouseout', removeClonedImages);
            }
        });
    });
});


document.addEventListener("DOMContentLoaded", () => {
    const op = document.querySelector('.op');
    const op_num = op ? op.getAttribute('id').split('p')[1] : null;
    const quotelinks = document.querySelectorAll("a.quotelink");

    quotelinks.forEach((quotelink) => {
        const post_num = quotelink.getAttribute("href").split("#p")[1];
        const board_shortname = quotelink.getAttribute('data-board_shortname');

        quotelink.addEventListener("mouseover", (e) => {
            const id_post_num = "#p" + post_num;
            let target_post = document.querySelector(id_post_num);

            quotelink_preview_hide();

            if (target_post == null) {
                fetch(`/${board_shortname}/post/${post_num}`)
                    .then(response => {
                        return response.ok ? response.json() : Promise.reject();
                    })
                    .then(data => {
                        let previewContent = data ? data.html_content : get_quotelink_preview_default_string();
                        target_post = document.createElement("div");
                        target_post.innerHTML = previewContent;
                        quotelink_preview_show(target_post, quotelink);
                    })
                    .catch(() => {
                        let default_preview = document.createElement("div");
                        default_preview.innerHTML = get_quotelink_preview_default_string();
                        quotelink_preview_show(default_preview, quotelink);
                    });
            } else {
                quotelink_preview_show(target_post, quotelink);
            }
        });

        quotelink.addEventListener("mouseleave", () => {
            quotelink_preview_hide();
        });

        // OP labels on quotelinks
        if(post_num == op_num) {
            quotelink.textContent += ' (OP)';
        }
    });
});


function get_quotelink_preview_default_string(){
    return `<div class="postContainer replyContainer">
        <div class="post reply">
            <div class="postInfo desktop">
                <span class="nameBlock">
                    <span class="name">Admin</span>
                </span>
            </div>
            <blockquote class="postMessage">Could not locate post</blockquote>
        </div>
    </div>`;
}


function quotelink_preview_hide(){
    document.querySelectorAll("#quote-preview").forEach(qp => {
        qp.remove()
    });
}

function quotelink_preview_show(target_post, quotelink) {
    let preview = target_post.cloneNode(true);
    preview.id = "quote-preview";

    document.body.appendChild(preview);

    const ql = quotelink.getBoundingClientRect();
    const prev = preview.getBoundingClientRect();
    const scroll_y = document.documentElement.scrollTop;

    // Default preview coordinates
    let top = ql.bottom + scroll_y - prev.height / 2;
    let left = ql.right + 5;

    // don't clip top
    if (top < scroll_y) {
        top = scroll_y;
    }

    // Flip side if there's not enough space on the right
    if (ql.right > window.innerWidth / 1.5) {
        left = ql.left - prev.width - 5;
    }

    // Adjust width to prevent clipping on the right
    if (left + prev.width > window.innerWidth) {
        preview.style.width = `${window.innerWidth - left - 10}px`;
    }

    // Set position
    preview.style.top = `${top}px`;
    preview.style.left = `${left}px`;
    preview.style.border = "1px solid white";
    preview.style.backgroundColor = "#282a2e";
}
