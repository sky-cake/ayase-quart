function remove_cloned_image() {
    const cloned_img = document.getElementById('img_cloned');
    if (cloned_img) {
        cloned_img.remove();
    }
}

function set_up_clickable_media() {
    const els = doc_query_all("img, .media_togg");
    for (const el of els) {
        el.removeEventListener("click", handleMediaClick);
        el.addEventListener("click", handleMediaClick);
    }
}

function handleMediaClick(e) {
    const el = e.currentTarget;
    const container = el.closest(".media_cont");
    if (!container) return;
    const media = container.querySelector("img, video");
    if (!media) return;

    expandMedia(media);
}

function expandMedia(e) {
    remove_cloned_image();
    const container = e.closest(".media_cont");
    const toggle = container?.querySelector(".media_togg");
    if (!container) return;

    const ext = e.dataset.ext;
    const isVideo = e.tagName.toLowerCase() === "video";
    const isExpanded = isVideo || e.dataset.expanded === "true";
    const isVideoType = ext_is_video(ext);

    const setLabel = open => {
        if (toggle) toggle.textContent = open ? "Close" : "Play";
    };

    if (isVideoType) {
        if (!isExpanded) {
            const video = document.createElement("video");
            video.id = e.id;
            video.controls = true;
            video.autoplay = true;
            video.style = "max-height:60vh;max-width:80vw;";
            video.dataset.ext = ext;
            video.dataset.thumb_src = e.dataset.thumb_src;
            video.dataset.full_media_src = e.dataset.full_media_src;
            video.dataset.width = e.dataset.width || e.getAttribute("width");
            video.dataset.height = e.dataset.height || e.getAttribute("height");
            if (e.dataset.class) video.dataset.class = e.dataset.class;

            const src = document.createElement("source");
            src.src = e.dataset.full_media_src;
            src.type = get_video_mimetype(ext);
            video.appendChild(src);
            video_interobs.observe(video);

            container.replaceChild(video, e);
            setLabel(true);
        } else {
            const img = document.createElement("img");
            img.id = e.id;
            img.src = e.dataset.thumb_src;
            img.dataset.expanded = "false";
            img.dataset.ext = ext;
            img.dataset.thumb_src = e.dataset.thumb_src;
            img.dataset.full_media_src = e.dataset.full_media_src;
            img.width = e.dataset.width || 250;
            img.height = e.dataset.height || 174;
            if (e.dataset.class) img.className = e.dataset.class;
            img.loading = "lazy";

            container.replaceChild(img, e);
            setLabel(false);
        }
    } else {
        if (isExpanded) {
            const img = document.createElement("img");
            img.id = e.id;
            img.src = e.dataset.thumb_src;
            img.dataset.expanded = "false";
            img.dataset.ext = ext;
            img.dataset.thumb_src = e.dataset.thumb_src;
            img.dataset.full_media_src = e.dataset.full_media_src;
            img.width = e.dataset.width || 250;
            img.height = e.dataset.height || 174;
            if (e.dataset.class) img.className = e.dataset.class;
            img.loading = "lazy";

            container.replaceChild(img, e);
        } else {
            const img = document.createElement("img");
            img.id = e.id;
            img.src = e.dataset.full_media_src;
            img.dataset.expanded = "true";
            img.dataset.ext = ext;
            img.dataset.thumb_src = e.dataset.thumb_src;
            img.dataset.full_media_src = e.dataset.full_media_src;
            img.dataset.width = e.dataset.width || e.getAttribute("width");
            img.dataset.height = e.dataset.height || e.getAttribute("height");
            if (e.dataset.class) img.dataset.class = e.dataset.class;
            img.style = "max-height:60vh;max-width:80vw;";
            img.removeAttribute("width");
            img.removeAttribute("height");

            container.replaceChild(img, e);
        }
    }

    setTimeout(set_up_clickable_media, 0);
}

function ext_is_video(ext) {
    return ["webm","mp4","ogg","mov"].includes(ext?.toLowerCase());
}
function get_video_mimetype(ext) {
    const m = {webm:"video/webm",mp4:"video/mp4",ogg:"video/ogg",mov:"video/quicktime"};
    return m[ext?.toLowerCase()] || "video/webm";
}

function set_up_board_buttons() {
    const allBtn = doc_query_all('.check_all_boards');
    const noneBtn = doc_query_all('.uncheck_all_boards');

    if (allBtn.length) {
        allBtn[0].addEventListener('click', () => {
            const checkboxes = doc_query_all('#boards input[type="checkbox"]');
            for (const checkbox of checkboxes) {
                checkbox.checked = true;
            }
        });
    }

    if (noneBtn.length) {
        noneBtn[0].addEventListener('click', () => {
            const checkboxes = doc_query_all('#boards input[type="checkbox"]');
            for (const checkbox of checkboxes) {
                checkbox.checked = false;
            }
        });
    }
}

function copy_link(button_element, path) {
    if (!path) return;

    const domain = window.location.origin.replace(/\/+$/, '');
    path = path.replace(/^\/+/, '');
    const link = `${domain}/${path}`;

    navigator.clipboard.writeText(link).then(() => {
		button_element.innerHTML = `✓`;
		setTimeout(() => {
			button_element.textContent = `©`;
		}, 1000);
	}).catch(err => {
		button_element.textContent = `x`;
	});
}

function copy_code(button_element, code, copy_text='©', success_text='✓', fail_text='x') {
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
    set_up_clickable_media();
    set_up_copy_buttons();
    set_up_board_buttons();
}

init_index();
