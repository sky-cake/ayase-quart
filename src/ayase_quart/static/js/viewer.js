let viewer_media_list = [];
let viewer_media_index = 0;

function viewer_update_scroll_lock() {
	const locked = !!document.getElementById('kuroba_overlay') || !!document.getElementById('viewer');
	document.body.classList.toggle('viewer_locked', locked);
}

function viewer_collect_media() {
	const list = [];
	for (const img of doc_query_all('.media_cont img[data-full_media_src]')) {
		const media_cont = img.closest('.media_cont');
		if (media_cont && media_cont.classList.contains('img_broken')) {
			continue;
		}
		list.push(img);
	}
	return list;
}

function viewer_thumb_click(thumb) {
	const full_src = get_data_string(thumb, 'full_media_src');
	if (!full_src) {
		return;
	}
	const list = viewer_collect_media();
	let index = -1;
	for (let i = 0; i < list.length; i++) {
		if (get_data_string(list[i], 'full_media_src') === full_src) {
			index = i;
			break;
		}
	}
	if (index === -1) {
		viewer_media_list = [thumb];
		viewer_open(0);
		return;
	}
	viewer_media_list = list;
	viewer_open(index);
}

function viewer_ensure() {
	let viewer = document.getElementById('viewer');
	if (viewer) {
		return viewer;
	}

	viewer = document.createElement('div');
	viewer.id = 'viewer';

	const media_div = document.createElement('div');
	media_div.id = 'viewer_media';

	const prev_btn = document.createElement('button');
	prev_btn.type = 'button';
	prev_btn.id = 'viewer_prev';
	prev_btn.textContent = '‹';
	prev_btn.title = 'Previous';

	const next_btn = document.createElement('button');
	next_btn.type = 'button';
	next_btn.id = 'viewer_next';
	next_btn.textContent = '›';
	next_btn.title = 'Next';

	const left_zone = document.createElement('div');
	left_zone.id = 'viewer_left';

	const right_zone = document.createElement('div');
	right_zone.id = 'viewer_right';

	const footer = document.createElement('div');
	footer.id = 'viewer_footer';
	const close_btn = document.createElement('button');
	close_btn.type = 'button';
	close_btn.id = 'viewer_close_btn';
	close_btn.classList.add('btn');
	close_btn.textContent = 'Close';
	footer.appendChild(close_btn);

	viewer.appendChild(media_div);
	viewer.appendChild(prev_btn);
	viewer.appendChild(next_btn);
	viewer.appendChild(left_zone);
	viewer.appendChild(right_zone);
	viewer.appendChild(footer);
	document.body.appendChild(viewer);
	return viewer;
}

function viewer_open(index) {
	viewer_media_index = index;
	viewer_ensure();
	viewer_render();
	viewer_update_scroll_lock();
}

function viewer_media_load_done() {
	const spinner = document.getElementById('viewer_spinner');
	if (spinner) {
		spinner.remove();
	}
}

function viewer_render() {
	const media_div = document.getElementById('viewer_media');
	media_div.replaceChildren();

	const spinner = document.createElement('div');
	spinner.id = 'viewer_spinner';
	media_div.appendChild(spinner);

	const item = viewer_media_list[viewer_media_index];
	const ext = get_data_string(item, 'ext');
	const full_src = get_data_string(item, 'full_media_src');

	if (ext_is_video(ext)) {
		const video = document.createElement('video');
		video.addEventListener('loadeddata', viewer_media_load_done);
		video.addEventListener('error', viewer_media_load_done);
		video.controls = true;
		video.autoplay = !!get_settings().autoplay_videos;
		video.muted = !!get_settings().mute_videos;
		video.src = full_src;
		const source = document.createElement('source');
		source.src = full_src;
		source.type = get_video_mimetype(ext);
		video.appendChild(source);
		media_div.appendChild(video);
	} else {
		const img = document.createElement('img');
		img.addEventListener('load', viewer_media_load_done);
		img.addEventListener('error', viewer_media_load_done);
		img.src = full_src;
		img.alt = '';
		media_div.appendChild(img);
	}

	document.getElementById('viewer_left').classList.toggle('viewer_zone_disabled', viewer_media_index === 0);
	document.getElementById('viewer_right').classList.toggle('viewer_zone_disabled', viewer_media_index === viewer_media_list.length - 1);
	document.getElementById('viewer_prev').classList.toggle('viewer_zone_disabled', viewer_media_index === 0);
	document.getElementById('viewer_next').classList.toggle('viewer_zone_disabled', viewer_media_index === viewer_media_list.length - 1);
}

function viewer_step(delta) {
	const next = viewer_media_index + delta;
	if (next < 0 || next >= viewer_media_list.length) {
		return;
	}
	viewer_media_index = next;
	viewer_render();
}

function viewer_close() {
	const viewer = document.getElementById('viewer');
	if (viewer) {
		viewer.remove();
	}
	viewer_update_scroll_lock();
}

function viewer_doc_click(event) {
	const target = event.target;

	const thumb = target.closest('img[data-full_media_src]');
	if (thumb) {
		if (thumb.closest('#catalog_threads')) {
			return;
		}
		event.preventDefault();
		viewer_thumb_click(thumb);
		return;
	}

	if (target.closest('#viewer_prev')) {
		viewer_step(-1);
		return;
	}

	if (target.closest('#viewer_next')) {
		viewer_step(1);
		return;
	}

	if (target.id === 'viewer_left') {
		viewer_step(-1);
		return;
	}

	if (target.id === 'viewer_right') {
		viewer_step(1);
		return;
	}

	if (target.id === 'viewer' || target.closest('#viewer_close_btn')) {
		viewer_close();
		return;
	}
}

function viewer_doc_keydown(event) {
	if (!document.getElementById('viewer')) {
		return;
	}

	const settings_modal = document.getElementById('settings_modal');
	if (settings_modal && settings_modal.style.display === 'block') {
		return;
	}

	if (event.key === 'Escape') {
		event.preventDefault();
		viewer_close();
	} else if (event.key === 'ArrowLeft') {
		viewer_step(-1);
	} else if (event.key === 'ArrowRight') {
		viewer_step(1);
	}
}

document.addEventListener('click', viewer_doc_click);
document.addEventListener('keydown', viewer_doc_keydown);
