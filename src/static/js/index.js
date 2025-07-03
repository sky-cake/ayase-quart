function removeClonedImages() {
    for (const img of document.querySelectorAll('#img_cloned')) {
        img.remove();
    }
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

// try full source for thumbnail if thumnail doesn't exist
// see template_optimizer.py
function p2other(el) {
    var ext = el.getAttribute("data-ext");
    if (ext === "webm" || ext === "mp4") {
 	   return;
    }
    const current_src = el.getAttribute('src');
    const thumb_src = el.getAttribute('data-thumb_src');
    const full_media_src = el.getAttribute('data-full_media_src');
    if (current_src === thumb_src && full_media_src) {
	    el.src = full_media_src;
    } else {
	    el.src = thumb_src;
    }
    el.onerror = null;
}

function checkAllBoards() {
    const checkboxes = document.querySelectorAll('#boards input[type="checkbox"]');
    for (const checkbox of checkboxes) {
        checkbox.checked = true;
    }
}

function uncheckAllBoards() {
    const checkboxes = document.querySelectorAll('#boards input[type="checkbox"]');
    for (const checkbox of checkboxes) {
        checkbox.checked = false;
    }
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

    navigator.clipboard.writeText(code).then(() => {
        button_element.innerHTML = success_text;
        setTimeout(() => {
            button_element.textContent = copy_text;
        }, 1000);
    }).catch(err => {
        button_element.textContent = fail_text;
    });
}

for (const codeElement of document.querySelectorAll('code')) {
    const copyButton = document.createElement('button');
    copyButton.innerHTML = `copy`;
    copyButton.classList.add('codecopybtn');

    codeElement.parentNode.insertBefore(copyButton, codeElement.nextSibling);

    copyButton.addEventListener('click', function () {
        const codeContent = codeElement.textContent;
        copy_code(copyButton, codeContent.replaceAll('<br>', '\n').replaceAll('&gt;', '>').replaceAll('&lt;', '<'), 'copy', 'copied', 'failed');
    });
}

function updateDateTimes() {
    const dateTimeElements = document.querySelectorAll('.dateTime');
    const now = new Date();
    for (const element of dateTimeElements) {
        const data_utc = get_data_integer(element, 'utc');
        if (data_utc) {
            const formattedString = format_timestamp(data_utc, now);
            element.textContent = formattedString;
        }
    }
}
updateDateTimes();

for (const el of document.querySelectorAll("[data-toggle]")) {
    el.addEventListener("click", () => {
        const idee = el.getAttribute("data-toggle");
        const target = document.getElementById(idee);
        if (target) {
        const isVisible = getComputedStyle(target).display !== "none";
        target.style.display = isVisible ? "none" : "block";
        }
    });
}

const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
        const video = entry.target;
        if (!(video instanceof HTMLVideoElement)) return;

        if (!entry.isIntersecting && !video.paused) {
            video.pause();
        }
    }}, {
        threshold: 0.1 // video is "visible" if at least 10% is in view
    }
);
    
for (const video of document.querySelectorAll('video')) {
    observer.observe(video);
}