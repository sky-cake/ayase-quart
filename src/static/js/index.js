


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

function expandMedia(e) {
    var ext = e.getAttribute("data-ext");
    
    if (ext === "webm") {
        var video = document.createElement("video");
        video.setAttribute("controls", true);
        video.setAttribute("autoplay", true);
        video.setAttribute("style", "max-height: 90vh; max-width: 90vw;");

        var source = document.createElement("source");
        source.setAttribute("src", e.getAttribute("data-full_media_src"));
        source.setAttribute("type", "video/webm");
        
        video.appendChild(source);

        e.parentNode.replaceChild(video, e);
        return;
    }

    var img = e.cloneNode();
    if (e.getAttribute("data-expanded") === "false"){
        img.setAttribute("data-expanded", "true");

        img.setAttribute("src", e.getAttribute("data-full_media_src"));
        
        img.setAttribute("style", "max-height: 90vh; max-width: 90vw;");
        img.setAttribute("data-width", e.getAttribute("width"));
        img.setAttribute("data-height", e.getAttribute("height"));
        img.removeAttribute("width", null);
        img.removeAttribute("height", null);
    }
    else{
        img.setAttribute("data-expanded", "false");
        
        img.removeAttribute("style");

        img.setAttribute("style", "max-height: 90vh; max-width: 90vw;");
        img.setAttribute("width", e.getAttribute("data-width"));
        img.setAttribute("height", e.getAttribute("data-height"));

        img.setAttribute("src", e.getAttribute("data-thumb_src"));


    }
    e.parentNode.replaceChild(img, e);
}

function pointToOtherMediaOnError(e) {
    var ext = e.getAttribute("data-ext");
    if (ext === "webm") {
        return;
    }

    const current_src = e.getAttribute('src');
    const thumb_src = e.getAttribute('data-thumb_src');
    const full_media_src = e.getAttribute('data-full_media_src');

    if (current_src === thumb_src && full_media_src){
        e.src = full_media_src;
    }
    else {
        e.src = thumb_src;
    }

    e.onerror = null;
}


function checkAllBoards() {
    document.querySelectorAll('#boards input[type="checkbox"]').forEach(function(checkbox) {
        checkbox.checked = true;
    });
}

function uncheckAllBoards() {
    document.querySelectorAll('#boards input[type="checkbox"]').forEach(function(checkbox) {
        checkbox.checked = false;
    });
}

