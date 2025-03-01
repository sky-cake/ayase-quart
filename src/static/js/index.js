function pointToOtherMediaOnError(e) {
  var ext = e.getAttribute("data-ext");
  if (ext === "webm" || ext === "mp4") {
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


function removeClonedImages() {
  document.querySelectorAll('#img_cloned').forEach(i => {i.remove()});
}


function expandMedia(e) {
  var ext = e.getAttribute("data-ext");

  removeClonedImages();
  
  if (ext === "webm" || ext === "mp4") {
      var video = document.createElement("video");
      video.setAttribute("controls", true);
      video.setAttribute("autoplay", true);
      video.setAttribute("style", "max-height: 60vh; max-width: 80vw;");

      var source = document.createElement("source");
      source.setAttribute("src", e.getAttribute("data-full_media_src"));
      ext === "webm" ? source.setAttribute("type", "video/webm") : source.setAttribute("type", "video/mp4");
      
      video.appendChild(source);

      e.parentNode.replaceChild(video, e);
      return;
  }

  var img = e.cloneNode();
  if (e.getAttribute("data-expanded") === "false"){
      img.setAttribute("data-expanded", "true");

      img.setAttribute("src", e.getAttribute("data-full_media_src"));
      
      img.setAttribute("style", "max-height: 60vh; max-width: 80vw;");
      img.setAttribute("data-width", e.getAttribute("width"));
      img.setAttribute("data-height", e.getAttribute("height"));
      img.removeAttribute("width", null);
      img.removeAttribute("height", null);
  }
  else{
      img.setAttribute("data-expanded", "false");
      
      img.removeAttribute("style");

      img.setAttribute("style", "max-height: 60vh; max-width: 80vw;");
      img.setAttribute("width", e.getAttribute("data-width"));
      img.setAttribute("height", e.getAttribute("data-height"));

      img.setAttribute("src", e.getAttribute("data-thumb_src"));

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
  }


  e.parentNode.replaceChild(img, e);
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