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


// quotelink hovering
document.addEventListener("DOMContentLoaded", () => {

    const op = document.querySelector('.op')
    const op_num = op ? op.getAttribute('id').split('p')[1] : null;
    
    const quotelinks = document.querySelectorAll("a.quotelink");

    quotelinks.forEach((quotelink) => {

        const post_num = quotelink.getAttribute("href").split("#p")[1];
        const board_shortname = quotelink.getAttribute('data-board_shortname');

        quotelink.addEventListener("mouseover", (e) => {
            const id_post_num = "#p" + post_num;
            var target_post = document.querySelector(id_post_num);

            if (target_post == null)
            {
                fetch(`/${board_shortname}/post/${post_num}`)
                .then(response => {
                    quotelink_preview_hide();
                    return response.json();
                })
                .catch(error => {
                    var target_post = document.createElement("div");
                    target_post.innerHTML = get_quotelink_preview_default_string();
                    quotelink_preview_show(target_post, quotelink);
                })
                .then(data => {
                    if (data){
                        var target_post = document.createElement("div");
                        target_post.innerHTML = data.html_content;
                        quotelink_preview_show(target_post, quotelink);
                    }
                });
            }
            else
            {
                quotelink_preview_show(target_post, quotelink);
            }
        });

        quotelink.addEventListener("mouseout", () => {
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


function quotelink_preview_show(target_post, quotelink){
    var preview = target_post.cloneNode(true);
    preview.id = "quote-preview"; // set the id to delete after mouse hover

    document.body.appendChild(preview);

    var ql = quotelink.getBoundingClientRect();

    var prev = preview.getBoundingClientRect();

    var scroll_y = document.documentElement.scrollTop;

    // default preview coords
    var top = ql.bottom + scroll_y - prev.height / 2;
    var left = ql.right + 5;
    var right = prev.right;

    // don't clip top
    if (top < scroll_y) {
        var top = scroll_y;
    }

    // flip side that preview quotelink is on if not much space on right side of it
    if (ql.right > window.outerWidth / 1.5) {
        left = ql.left - prev.width - 5;
    }

    // don't clip right
    if (right > window.outerWidth) {
        preview.style.width = window.outerWidth - right - 10 + "px";
    }

    // don't clip left
    if (left < 0) {
        left = 0;
        if (right > ql.left) {
            preview.style.width = ql.left - 10 + "px";
        }
    }

    preview.style.top = top + "px";
    preview.style.left = left + "px";
    
    preview.style.border = "1px solid white";
    preview.style.backgroundColor = "#282a2e"; // TODO: support other themes
}
