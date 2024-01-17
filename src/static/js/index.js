document.addEventListener("DOMContentLoaded", () => {

    const op_num = document.querySelector('.op').getAttribute('id').split('p')[1];
    
    const quotelinks = document.querySelectorAll("a.quotelink");

    quotelinks.forEach((quotelink) => {

        const post_num = quotelink.getAttribute("href").split("#p")[1]

        quotelink.addEventListener("mouseover", (e) => {
            const id_post_num = "#p" + post_num;
            var target_post = document.querySelector(id_post_num);

            // post might be deleted, in this case make an element
            if (target_post == null) {
                target_post = document.createElement("div");
                target_post.innerHTML = `<div class="postContainer replyContainer">
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
        });


        quotelink.addEventListener("mouseout", () => {
            document.getElementById("quote-preview").remove();
        });


        // OP labels on quotelinks
        if(post_num == op_num) {
            quotelink.textContent += ' (OP)';
        }


    });

});
