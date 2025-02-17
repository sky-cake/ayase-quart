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
  
  const op = document.querySelector('.op');
  const op_num = op ? op.getAttribute('id').split('p')[1] : null;
  const quotelinks = document.querySelectorAll("a.quotelink");

  quotelinks.forEach((quotelink) => {
      const num = quotelink.getAttribute("href").split("#p")[1];
      const board_shortname = quotelink.getAttribute('data-board_shortname');

      quotelink.addEventListener("mouseover", (e) => {
          let backlink = e.target.parentElement.parentElement.id;
          let backlink_num = backlink ? backlink.replace(/^bl_/, '') : null;
          
          const id_post_num = "#p" + num;
          let target_post = document.querySelector(id_post_num);

          quotelink_preview_hide();

          if (target_post == null) {
              fetch(`/${board_shortname}/post/${num}`)
                  .then(response => {
                      return response.ok ? response.json() : Promise.reject();
                  })
                  .then(data => {
                      let previewContent = data ? data.html_content : get_quotelink_preview_default_string();
                      target_post = document.createElement("div");
                      target_post.innerHTML = previewContent;
                      quotelink_preview_show(target_post, quotelink, backlink_num);
                  })
                  .catch(() => {
                      let default_preview = document.createElement("div");
                      default_preview.innerHTML = get_quotelink_preview_default_string();
                      quotelink_preview_show(default_preview, quotelink, backlink_num);
                  });
          } else {
              quotelink_preview_show(target_post, quotelink, backlink_num);
          }
      });

      quotelink.addEventListener("mouseleave", () => {
          quotelink_preview_hide();
      });

      // OP labels on quotelinks
      if(num == op_num) {
          quotelink.textContent += ' (OP)';
      }
  });
});

function get_quotelink_preview_default_string(){
  return `<div class="postContainer replyContainer"><div class="post reply">
    <div class="postInfo desktop"><span class="nameBlock"><span class="name">Admin</span></span></div>
    <blockquote class="postMessage">Could not locate post</blockquote>
</div></div>`;
}

function quotelink_preview_hide(){
  document.querySelectorAll("#quote-preview").forEach(qp => {qp.remove()});
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

  preview.addEventListener("mouseover", (e) => {quotelink_preview_hide();});

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