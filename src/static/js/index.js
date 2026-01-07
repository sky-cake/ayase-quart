function remove_overlay_image() {
    const cloned_img = document.getElementById('img_cloned');
    if (cloned_img) {
        cloned_img.remove();
    }
}

function invert_video_btn(el, is_playing) {
    if (!el) return;

    el.textContent = is_playing ? "Close" : "Play";

    if (is_playing){
        el.removeEventListener('click', play_video_via_btn);
        el.addEventListener('click', close_video_via_btn);
    } else {
        el.removeEventListener('click', close_video_via_btn);
        el.addEventListener('click', play_video_via_btn);
    }
}

function ext_is_video(ext) {
    return ["webm","mp4","ogg","mov"].includes(ext?.toLowerCase());
}

function get_video_mimetype(ext) {
    const m = {webm:"video/webm",mp4:"video/mp4",ogg:"video/ogg",mov:"video/quicktime"};
    return m[ext?.toLowerCase()] || "video/webm";
}

function set_up_board_buttons() {
    const all_btn = doc_query_all('.check_all_boards');
    const none_btn = doc_query_all('.uncheck_all_boards');

    if (all_btn.length) {
        all_btn[0].addEventListener('click', () => {
            const checkboxes = doc_query_all('#boards input[type="checkbox"]');
            for (const checkbox of checkboxes) {
                checkbox.checked = true;
            }
        });
    }

    if (none_btn.length) {
        none_btn[0].addEventListener('click', () => {
            const checkboxes = doc_query_all('#boards input[type="checkbox"]');
            for (const checkbox of checkboxes) {
                checkbox.checked = false;
            }
        });
    }
}

function update_datetimes() {
    const datetime_els = doc_query_all('.dateTime');
    const is_catalog = Boolean(document.getElementById('catalog_threads'));
    const now = new Date();
    for (const datetime_el of datetime_els) {
        const data_utc = get_data_integer(datetime_el, 'utc');
        if (data_utc) {
            const formattedString = format_timestamp(data_utc, now, is_catalog);
            datetime_el.innerHTML = formattedString;
        }
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

function set_video_intersection_events() {
	for (const video of doc_query_all('video')) {
		video_interobs.observe(video);
	}
}

function set_image_toggle(e) {
    const clicked_img = e.target;
    const is_expanded = clicked_img.dataset.expanded === "true";

    const new_img = document.createElement("img");

    new_img.dataset.ext = clicked_img.dataset.ext;
    new_img.dataset.thumb_src = clicked_img.dataset.thumb_src;
    new_img.dataset.full_media_src = clicked_img.dataset.full_media_src;

    new_img.id = clicked_img.id;
    new_img.loading = "lazy";

    if (clicked_img.classList) {
        new_img.classList = clicked_img.classList;
    }

    if (is_expanded){
        new_img.dataset.expanded = "false";

        new_img.src = new_img.dataset.thumb_src;

        new_img.width = clicked_img.dataset.width;
        new_img.height = clicked_img.dataset.height;
    } else {
        new_img.dataset.expanded = "true";

        new_img.src = new_img.dataset.full_media_src;

        new_img.dataset.width = clicked_img.getAttribute("width");
        new_img.dataset.height = clicked_img.getAttribute("height");

        new_img.removeAttribute("width");
        new_img.removeAttribute("height");
    }

    remove_overlay_image();
    clicked_img.parentNode.replaceChild(new_img, clicked_img);

    new_img.addEventListener('click', set_image_toggle);
}

function set_up_image_toggles() {
    // Images can be opened and closed by clicking them
    for (const image of doc_query_all('img.mtog.is_image')) {
        image.addEventListener('click', set_image_toggle);
    }
}

function close_video_via_btn(e) {
    const close_btn = e.target;

    const close_video = close_btn.parentNode.querySelector('video');
    if (!close_video) {
        console.error('couldnt find video for close button', close_video);
        return;
    }

    const new_img = document.createElement("img");

    new_img.id = close_video.id;
    new_img.src = close_video.dataset.thumb_src;
    new_img.width = close_video.dataset.width;
    new_img.height = close_video.dataset.height;
    new_img.loading = "lazy";

    new_img.dataset.ext = close_video.dataset.ext;
    new_img.dataset.thumb_src = close_video.dataset.thumb_src;
    new_img.dataset.full_media_src = close_video.dataset.full_media_src;

    if (e.classList) {
        new_img.classList = close_video.classList;
    }
    new_img.classList.add('play');

    remove_overlay_image();
    invert_video_btn(close_btn, false);
    new_img.addEventListener('click', play_video_via_thumb_click);
    close_btn.parentNode.replaceChild(new_img, close_video);
}

function play_video_via_thumb_click(e) {
    const video_thumb = e.target;
    const play_btn = video_thumb.parentNode.querySelector('span.mtog.play');
    if (!play_btn) {
        console.error('couldnt find the play button for the video thumbnail')
    }
    replace_thumb_with_video(video_thumb);
    invert_video_btn(play_btn, true);
}

function play_video_via_btn(e) {
    const play_btn = e.target;
    const video_thumb = play_btn.parentNode.querySelector('img');
    if (!video_thumb) {
        console.error('couldnt find video thumbnail for play button', video_thumb);
        return;
    }
    invert_video_btn(play_btn, true);
    replace_thumb_with_video(video_thumb);
}

function replace_thumb_with_video(video_thumb) {
    const new_video = document.createElement("video");

    new_video.dataset.ext = video_thumb.dataset.ext;
    new_video.dataset.thumb_src = video_thumb.dataset.thumb_src;
    new_video.dataset.full_media_src = video_thumb.dataset.full_media_src;
    new_video.dataset.width = video_thumb.width;
    new_video.dataset.height = video_thumb.height;

    new_video.id = video_thumb.id;
    new_video.src = new_video.dataset.full_media_src;
    new_video.controls = true;
    new_video.autoplay = true;
    new_video.loading = "lazy";

    if (video_thumb.classList) {
        new_video.classList = video_thumb.classList;
    }
    new_video.classList.add('close');

    const new_source = document.createElement("source");
    new_source.src = video_thumb.dataset.full_media_src;
    new_source.type = get_video_mimetype(video_thumb.dataset.ext);
    new_video.appendChild(new_source);

    video_interobs.observe(new_video);

    remove_overlay_image();
    video_thumb.parentNode.replaceChild(new_video, video_thumb);
    new_video.addEventListener('click', close_video_via_btn);
}

function set_up_video_toggles() {
    // Videos can be opened and closed by clicking a Play/Close button
    for (const play_btn of doc_query_all('span.mtog.play')) {
        play_btn.addEventListener('click', play_video_via_btn);
    }
    // Videos can be opened by clicking their thumbnail
    for (const vid_thumb of doc_query_all('img.mtog.is_video')) {
        vid_thumb.addEventListener('click', play_video_via_thumb_click);
    }
}

function init_index() {
	update_datetimes();
	set_video_intersection_events();
    set_up_image_toggles();
    set_up_video_toggles();
    set_up_board_buttons();
}

init_index();
