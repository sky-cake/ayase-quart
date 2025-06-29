function removeClonedImages() {
  document.querySelectorAll('#img_cloned').forEach(i => i.remove());
}

function expandMedia(e) {
  removeClonedImages();
  const ext = e.getAttribute("data-ext");
  const container = e.closest('.media_cont');
  const toggleSpan = container?.querySelector('.media_togg');

  const updateToggleLabel = (open) => {
    if (toggleSpan) toggleSpan.textContent = open ? "Close" : "Play";
  };

  const isVideo = ext === "webm" || ext === "mp4";
  const isVideoExpanded = e.tagName.toLowerCase() === "video";
  const isImageExpanded = e.getAttribute("data-expanded") === "true";

  if (isVideo && !isVideoExpanded) {
    const fullSrc = e.getAttribute("data-full_media_src");
    if (!fullSrc) return;

    const video = document.createElement("video");
    video.id = e.id;
    video.controls = true;
    video.autoplay = true;
    video.style = "max-height: 60vh; max-width: 80vw;";
    video.setAttribute("data-ext", ext);
    video.setAttribute("data-thumb_src", e.getAttribute("data-thumb_src"));
    video.setAttribute("data-full_media_src", fullSrc);
    video.setAttribute("data-width", e.getAttribute("width"));
    video.setAttribute("data-height", e.getAttribute("height"));
    if (e.getAttribute("class")) {
      video.setAttribute("data-class", e.getAttribute("class"));
    }
    video.onclick = () => expandMedia(video);

    const source = document.createElement("source");
    source.src = fullSrc;
    source.type = ext === "webm" ? "video/webm" : "video/mp4";
    video.appendChild(source);
    observer.observe(video); // pause videos when out of view

    container.replaceChild(video, e);
    updateToggleLabel(true);
    return;
  }

  const img = document.createElement("img");
  img.id = e.id;
  img.setAttribute("data-ext", ext);
  img.setAttribute("data-thumb_src", e.getAttribute("data-thumb_src"));
  img.setAttribute("data-full_media_src", e.getAttribute("data-full_media_src"));
  if (e.getAttribute("class")) {
    img.setAttribute("data-class", e.getAttribute("class"));
  }
  img.style = "max-height: 60vh; max-width: 80vw;";
  img.onclick = () => expandMedia(img);

  if (isVideoExpanded || isImageExpanded) {
    img.setAttribute("data-expanded", "false");
    img.src = e.getAttribute("data-thumb_src");
    if (e.getAttribute("data-class")) {
      img.classList.add(e.getAttribute("data-class"));
    }
    img.width = e.getAttribute("data-width") || 300;
    img.height = e.getAttribute("data-height") || 300;
    updateToggleLabel(false);
  } else {
    img.setAttribute("data-expanded", "true");
    img.src = e.getAttribute("data-full_media_src");
    img.setAttribute("data-width", e.getAttribute("width"));
    img.setAttribute("data-height", e.getAttribute("height"));
    img.removeAttribute("width");
    img.removeAttribute("height");
    updateToggleLabel(true);
  }

  container.replaceChild(img, e);
}

function checkAllBoards() {
  document.querySelectorAll('#boards input[type="checkbox"]').forEach(function (checkbox) {
    checkbox.checked = true;
  });
}

function uncheckAllBoards() {
  document.querySelectorAll('#boards input[type="checkbox"]').forEach(function (checkbox) {
    checkbox.checked = false;
  });
}

function copy_link(button_element, path) {
  if (!path) return;

  const domain = window.location.origin.replace(/\/+$/, '');
  path = path.replace(/^\/+/, '');
  const link = `${domain}/${path}`;

  navigator.clipboard.writeText(link)
    .then(() => {
      button_element.innerHTML = `&checkmark;`;
      setTimeout(() => {
        button_element.textContent = `⎘`;
      }, 1000);
    })
    .catch(err => {
      button_element.textContent = `x`;
    });
}

function copy_code(button_element, code, copy_text='⎘', success_text='&checkmark;', fail_text='x') {
  if (!code) return;

  navigator.clipboard.writeText(code)
    .then(() => {
      button_element.innerHTML = success_text;
      setTimeout(() => {
        button_element.textContent = copy_text;
      }, 1000);
    })
    .catch(err => {
      button_element.textContent = fail_text;
    });
}

document.querySelectorAll('code').forEach(function (codeElement) {
  const copyButton = document.createElement('button');
  copyButton.innerHTML = `copy`;
  copyButton.classList.add('codecopybtn');

  codeElement.parentNode.insertBefore(copyButton, codeElement.nextSibling);

  copyButton.addEventListener('click', function () {
    const codeContent = codeElement.textContent;
    copy_code(copyButton, codeContent.replaceAll('<br>', '\n').replaceAll('&gt;', '>').replaceAll('&lt;', '<'), 'copy', 'copied', 'failed');
  });
});


function tsToFormatted(ts) {
  const postDate = new Date(ts * 1000);
  const now = new Date();
  const delta = now - postDate;

  const options = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short' 
  };
  const formattedDate = postDate.toLocaleString(undefined, options);

  const seconds = Math.floor(delta / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const months = Math.floor(days / 30);
  const years = Math.floor(days / 365);

  let relativeTime = 'now';
  if (years > 0) {
      relativeTime = `${years} year${years > 1 ? 's' : ''} ago`;
  } else if (months > 0) {
      relativeTime = `${months} month${months > 1 ? 's' : ''} ago`;
  } else if (days > 0) {
      relativeTime = `${days} day${days > 1 ? 's' : ''} ago`;
  } else if (hours > 0) {
      relativeTime = `${hours} hour${hours > 1 ? 's' : ''} ago`;
  } else if (minutes > 0) {
      relativeTime = `${minutes} min${minutes > 1 ? 's' : ''} ago`;
  } else if (seconds > 0) {
      relativeTime = `${seconds} sec${seconds > 1 ? 's' : ''} ago`;
  }

  return `${formattedDate} (${relativeTime})`;
}

function updateDateTimes() {
  const dateTimeElements = document.querySelectorAll('.dateTime');
  dateTimeElements.forEach(element => {
      data_utc = element.getAttribute('data-utc');
      if (data_utc) {
        const utcTimestamp = parseInt(element.getAttribute('data-utc'), 10);
        const formattedString = tsToFormatted(utcTimestamp);
        element.textContent = formattedString;
      }
  });
}
updateDateTimes();

document.querySelectorAll("[data-toggle]").forEach(el => {
  el.addEventListener("click", () => {
    const idee = el.getAttribute("data-toggle");
    const target = document.getElementById(idee);
    if (target) {
      const isVisible = getComputedStyle(target).display !== "none";
      target.style.display = isVisible ? "none" : "block";
    }
  });
});

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    const video = entry.target;
    if (!(video instanceof HTMLVideoElement)) return;

    if (!entry.isIntersecting && !video.paused) {
      video.pause();
    }
  });
}, {
  threshold: 0.1 // video is "visible" if at least 10% is in view
});

document.querySelectorAll('video').forEach(video => {
  observer.observe(video);
});
