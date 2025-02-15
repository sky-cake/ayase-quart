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


function removeClonedImages() {
  document.querySelectorAll('#img_cloned').forEach(i => {i.remove()});
}


function expandMedia(e) {
  var ext = e.getAttribute("data-ext");

  removeClonedImages();
  
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