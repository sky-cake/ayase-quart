function remove_cloned_image() {
    const cloned_img = document.getElementById('img_cloned');
    if (cloned_img) {
        cloned_img.remove();
    }
}

function expandMedia(e) {
    remove_cloned_image();
    const ext = get_data_string(e, 'ext')
    const container = e.closest('.media_cont');
    const toggleSpan = container?.querySelector('.media_togg');

    const updateToggleLabel = (open) => {
        if (toggleSpan) toggleSpan.textContent = open ? "Close" : "Play";
    };

    const isVideoExpanded = e.tagName.toLowerCase() === "video";
    const isImageExpanded = e.getAttribute("data-expanded") === "true";

    if (ext_is_video(ext) && !isVideoExpanded) {
        const fullSrc = e.getAttribute("data-full_media_src");
        if (!fullSrc) return;

        const video = document.createElement("video");
        video.id = e.id;
        video.controls = true;
        video.autoplay = true;
        video.style = "max-height: 60vh; max-width: 80vw;";
        video.dataset.ext = ext;
        video.dataset.thumb_src = e.getAttribute("data-thumb_src");
        video.dataset.full_media_src = fullSrc;
        video.dataset.width = e.getAttribute("width");
        video.dataset.height = e.getAttribute("height");
        if (e.getAttribute("class")) {
            video.setAttribute("data-class", e.getAttribute("class"));
        }
        video.onclick = () => expandMedia(video);

        const source = document.createElement("source");
        source.src = fullSrc;
        source.type = get_video_mimetype(ext);
        video.appendChild(source);
        video_interobs.observe(video); // pause videos when out of view

        container.replaceChild(video, e);
        updateToggleLabel(true);
        return;
    }

    const img = document.createElement("img");
    img.id = e.id;
    img.dataset.ext = ext;
    img.dataset.thumb_src = e.getAttribute("data-thumb_src");
    img.dataset.full_media_src = e.getAttribute("data-full_media_src");
    if (e.getAttribute("class")) {
        img.dataset.class = e.getAttribute("class");
    }
    img.style = "max-height: 60vh; max-width: 80vw;";
    img.onclick = () => expandMedia(img);

    if (isVideoExpanded || isImageExpanded) {
        img.dataset.expanded = "false";
        img.src = e.getAttribute("data-thumb_src");
        if (e.getAttribute("data-class")) {
            img.classList.add(e.getAttribute("data-class"));
        }
        img.width = e.getAttribute("data-width") || 300;
        img.height = e.getAttribute("data-height") || 300;
        updateToggleLabel(false);
    } else {
        img.dataset.expanded = "true";
        img.src = e.getAttribute("data-full_media_src");
        img.dataset.width = e.getAttribute("width");
        img.dataset.height = e.getAttribute("height");
        img.removeAttribute("width");
        img.removeAttribute("height");
        updateToggleLabel(true);
    }

    container.replaceChild(img, e);
}

function checkAllBoards() {
    const checkboxes = doc_query_all('#boards input[type="checkbox"]');
    for (const checkbox of checkboxes) {
        checkbox.checked = true;
    }
}

function uncheckAllBoards() {
    const checkboxes = doc_query_all('#boards input[type="checkbox"]');
    for (const checkbox of checkboxes) {
        checkbox.checked = false;
    }
}

function copy_link(button_element, path) {
    if (!path) return;

    const domain = window.location.origin.replace(/\/+$/, '');
    path = path.replace(/^\/+/, '');
    const link = `${domain}/${path}`;

    navigator.clipboard.writeText(link).then(() => {
		button_element.innerHTML = `&checkmark;`;
		setTimeout(() => {
			button_element.textContent = `⎘`;
		}, 1000);
	}).catch(err => {
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

function setup_code_clipboard() {
	for (const codeElement of doc_query_all('code')) {
		const copyButton = document.createElement('button');
		copyButton.innerHTML = `copy`;
		copyButton.classList.add('codecopybtn');
	
		codeElement.parentNode.insertBefore(copyButton, codeElement.nextSibling);
	
		copyButton.addEventListener('click', function () {
			const codeContent = codeElement.textContent;
			copy_code(copyButton, codeContent.replaceAll('<br>', '\n').replaceAll('&gt;', '>').replaceAll('&lt;', '<'), 'copy', 'copied', 'failed');
		});
	}
}

function updateDateTimes() {
    const dateTimeElements = doc_query_all('.dateTime');
    const now = new Date();
    for (const element of dateTimeElements) {
        const data_utc = get_data_integer(element, 'utc');
        if (data_utc) {
            const formattedString = format_timestamp(data_utc, now);
            element.textContent = formattedString;
        }
    }
}

// fts
function setup_data_toggles() {
	for (const el of doc_query_all("[data-toggle]")) {
		el.addEventListener("click", () => {
			const idee = get_data_string(el, 'toggle');
			const target = document.getElementById(idee);
			if (target) {
				const isVisible = getComputedStyle(target).display !== "none";
				target.style.display = isVisible ? "none" : "block";
			}
		});
	}
}

// global variable video expand
const video_interobs = new IntersectionObserver((entries) => {
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

function setup_video_intersection_events() {
	for (const video of doc_query_all('video')) {
		video_interobs.observe(video);
	}
}

function set_up_clickable_images() {
    const els = doc_query_all("img");
    for (const el of els) {
        el.addEventListener("click", () => {
            expandMedia(el)
        });
    }
}

function set_up_copy_buttons() {
    const els = doc_query_all('.copy_link');
    for (const el of els) {
        el.addEventListener('click', () => {
            copy_link(el, el.dataset.link);
        });
    }
}

function init_index() {
	updateDateTimes();
	setup_data_toggles();
	setup_video_intersection_events();
    set_up_clickable_images();
    set_up_copy_buttons();
}

init_index();
