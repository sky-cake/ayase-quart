let kuroba_view_stack = [];
const kuroba_post_cache = new Map();
const kuroba_post_fetching = new Set();

function kuroba_num_from_quotelink(quotelink) {
	return parseInt(quotelink.getAttribute('href').split('#p')[1], 10);
}

function kuroba_get_reply_nums(num) {
	const nums = [];
	const backlink_div = document.getElementById('bl_' + num);
	if (!backlink_div) {
		return nums;
	}
	for (const link of backlink_div.querySelectorAll('a.quotelink')) {
		nums.push(kuroba_num_from_quotelink(link));
	}
	return nums;
}

function kuroba_make_replies_btn(num) {
	const btn = document.createElement('button');
	btn.type = 'button';
	btn.classList.add('kuroba_replies_btn');
	btn.classList.add('btn');
	btn.dataset.num = String(num);
	const count = kuroba_get_reply_nums(num).length;
	btn.textContent = count === 1 ? '1 reply' : `${count} replies`;
	return btn;
}

function kuroba_build_media(media_img) {
	const source_cont = media_img.closest('.media_cont');
	if (source_cont && source_cont.classList.contains('img_broken')) {
		const broken = document.createElement('div');
		broken.classList.add('media_cont');
		broken.classList.add('img_broken');
		return broken;
	}
	const media_cont = document.createElement('div');
	media_cont.classList.add('media_cont');
	const thumb = media_img.cloneNode(false);
	thumb.removeAttribute('id');
	thumb.removeAttribute('data-expanded');
	thumb.classList.add('kuroba_thumb');
	media_cont.appendChild(thumb);
	return media_cont;
}

function kuroba_build_entry(num) {
	const entry = document.createElement('div');
	entry.classList.add('kuroba_entry');

	const content = document.createElement('div');
	content.classList.add('kuroba_entry_content');

	const header = document.createElement('div');
	header.classList.add('kuroba_entry_header');
	const no_span = document.createElement('span');
	no_span.classList.add('kuroba_entry_no');
	no_span.textContent = `No.${num}`;
	header.appendChild(no_span);

	const post_info = document.getElementById('pi' + num);
	if (post_info) {
		const datetime = post_info.querySelector('.dateTime');
		if (datetime) {
			header.appendChild(datetime.cloneNode(true));
		}
	}
	content.appendChild(header);

	const media_img = document.querySelector(`#p${num} .media_cont img.mtog`);
	if (media_img) {
		content.appendChild(kuroba_build_media(media_img));
	}

	const comment = document.getElementById('m' + num);
	if (comment) {
		const blockquote = comment.cloneNode(false);
		blockquote.removeAttribute('id');
		blockquote.classList.add('kuroba_entry_comment');
		blockquote.innerHTML = comment.innerHTML;
		content.appendChild(blockquote);
	}

	if (kuroba_get_reply_nums(num).length > 0) {
		content.appendChild(kuroba_make_replies_btn(num));
	}

	entry.appendChild(content);

	const goto_btn = document.createElement('button');
	goto_btn.type = 'button';
	goto_btn.classList.add('kuroba_goto_btn');
	goto_btn.classList.add('btn');
	goto_btn.dataset.num = String(num);
	goto_btn.textContent = '→';
	goto_btn.title = 'Go to post';
	entry.appendChild(goto_btn);

	return entry;
}

function kuroba_get_board() {
	const tools = document.getElementById('tools');
	return get_data_string(tools, 'board');
}

function kuroba_post_response_to_json(response) {
	return response.ok ? response.json() : Promise.reject();
}

function kuroba_store_post_response(post_key, data) {
	kuroba_post_fetching.delete(post_key);
	if (data && data.html_content) {
		kuroba_post_cache.set(post_key, data);
	} else {
		kuroba_post_cache.set(post_key, {});
	}
	if (document.getElementById('kuroba_overlay')) {
		kuroba_render_modal();
	}
}

function kuroba_store_post_error(post_key) {
	kuroba_post_fetching.delete(post_key);
	kuroba_post_cache.set(post_key, {});
	if (document.getElementById('kuroba_overlay')) {
		kuroba_render_modal();
	}
}

function kuroba_fetch_post(post_key) {
	if (kuroba_post_cache.has(post_key) || kuroba_post_fetching.has(post_key)) {
		return;
	}
	kuroba_post_fetching.add(post_key);
	fetch(post_key)
		.then(kuroba_post_response_to_json)
		.then(kuroba_store_post_response.bind(null, post_key))
		.catch(kuroba_store_post_error.bind(null, post_key));
}

function kuroba_build_loading() {
	const div = document.createElement('div');
	div.classList.add('kuroba_empty');
	div.textContent = 'Loading...';
	return div;
}

function kuroba_build_not_found() {
	const div = document.createElement('div');
	div.classList.add('kuroba_empty');
	div.textContent = 'Could not find post.';
	return div;
}

function kuroba_build_cross_entry(num, data) {
	const container = document.createElement('div');
	container.innerHTML = data.html_content;
	const post = container.querySelector('.post');

	const entry = document.createElement('div');
	entry.classList.add('kuroba_entry');

	const content = document.createElement('div');
	content.classList.add('kuroba_entry_content');

	const header = document.createElement('div');
	header.classList.add('kuroba_entry_header');
	const no_span = document.createElement('span');
	no_span.classList.add('kuroba_entry_no');
	no_span.textContent = `No.${num}`;
	header.appendChild(no_span);

	if (post) {
		const datetime = post.querySelector('.dateTime');
		if (datetime) {
			header.appendChild(datetime.cloneNode(true));
		}
	}
	content.appendChild(header);

	if (post) {
		const media_img = post.querySelector('.media_cont img.mtog');
		if (media_img) {
			content.appendChild(kuroba_build_media(media_img));
		}

		const comment = post.querySelector('.postMessage');
		if (comment) {
			const blockquote = document.createElement('blockquote');
			blockquote.classList.add('postMessage');
			blockquote.classList.add('kuroba_entry_comment');
			blockquote.innerHTML = comment.innerHTML;
			content.appendChild(blockquote);
		}
	}

	entry.appendChild(content);

	const goto_btn = document.createElement('button');
	goto_btn.type = 'button';
	goto_btn.classList.add('kuroba_goto_btn');
	goto_btn.classList.add('btn');
	goto_btn.dataset.num = String(num);
	if (data.thread_num) {
		goto_btn.dataset.thread = String(data.thread_num);
	}
	goto_btn.textContent = '→';
	goto_btn.title = 'Go to post';
	entry.appendChild(goto_btn);

	return entry;
}

function kuroba_ensure_modal() {
	let overlay = document.getElementById('kuroba_overlay');
	if (overlay) {
		return overlay;
	}

	overlay = document.createElement('div');
	overlay.id = 'kuroba_overlay';

	const modal = document.createElement('div');
	modal.id = 'kuroba_modal';
	modal.classList.add('form');

	const body = document.createElement('div');
	body.id = 'kuroba_modal_body';

	const footer = document.createElement('div');
	footer.id = 'kuroba_modal_footer';
	const back_btn = document.createElement('button');
	back_btn.type = 'button';
	back_btn.id = 'kuroba_back';
	back_btn.classList.add('btn');
	back_btn.textContent = 'Back';
	const close_btn = document.createElement('button');
	close_btn.type = 'button';
	close_btn.id = 'kuroba_close';
	close_btn.classList.add('btn');
	close_btn.textContent = 'Close';
	footer.appendChild(close_btn);
	footer.appendChild(back_btn);

	modal.appendChild(body);
	modal.appendChild(footer);
	overlay.appendChild(modal);
	document.body.appendChild(overlay);
	return overlay;
}

function kuroba_render_modal() {
	kuroba_ensure_modal();
	const view = kuroba_view_stack[kuroba_view_stack.length - 1];

	const body = document.getElementById('kuroba_modal_body');
	body.replaceChildren();

	if (view.type === 'replies') {
		const nums = kuroba_get_reply_nums(view.num);
		if (nums.length === 0) {
			const empty = document.createElement('div');
			empty.classList.add('kuroba_empty');
			empty.textContent = 'No replies';
			body.appendChild(empty);
		} else {
			for (const num of nums) {
				body.appendChild(kuroba_build_entry(num));
			}
		}
	} else if (view.type === 'cross_post') {
		const data = kuroba_post_cache.get(`/${kuroba_get_board()}/post/${view.num}`);
		if (!data) {
			body.appendChild(kuroba_build_loading());
		} else if (!data.html_content) {
			body.appendChild(kuroba_build_not_found());
		} else {
			body.appendChild(kuroba_build_cross_entry(view.num, data));
		}
	} else {
		body.appendChild(kuroba_build_entry(view.num));
	}

	document.getElementById('kuroba_back').disabled = kuroba_view_stack.length <= 1;
	body.scrollTop = 0;
	update_datetimes(body);
}

function kuroba_open_post_view(num) {
	if (document.getElementById('p' + num)) {
		kuroba_view_stack.push({ type: 'post', num: num });
		kuroba_render_modal();
		viewer_update_scroll_lock();
		return;
	}
	kuroba_view_stack.push({ type: 'cross_post', num: num });
	kuroba_render_modal();
	viewer_update_scroll_lock();
	kuroba_fetch_post(`/${kuroba_get_board()}/post/${num}`);
}

function kuroba_open_replies_view(num) {
	kuroba_view_stack.push({ type: 'replies', num: num });
	kuroba_render_modal();
	viewer_update_scroll_lock();
}

function kuroba_back() {
	kuroba_view_stack.pop();
	if (kuroba_view_stack.length === 0) {
		kuroba_close_modal();
		return;
	}
	kuroba_render_modal();
}

function kuroba_close_modal() {
	const overlay = document.getElementById('kuroba_overlay');
	if (overlay) {
		overlay.remove();
	}
	kuroba_view_stack = [];
	viewer_update_scroll_lock();
}

function kuroba_goto_post(num) {
	const post = document.getElementById('p' + num);
	if (!post) {
		return;
	}
	post.scrollIntoView({ block: 'start' });
	post.classList.remove('kuroba_target_flash');
	void post.offsetWidth;
	post.classList.add('kuroba_target_flash');
}

function kuroba_doc_click(event) {
	const target = event.target;

	const quotelink = target.closest('a.quotelink');
	if (quotelink) {
		event.preventDefault();
		kuroba_open_post_view(kuroba_num_from_quotelink(quotelink));
		return;
	}

	const replies_btn = target.closest('.kuroba_replies_btn');
	if (replies_btn) {
		kuroba_open_replies_view(parseInt(replies_btn.dataset.num, 10));
		return;
	}

	if (target.closest('#kuroba_back')) {
		kuroba_back();
		return;
	}

	if (target.closest('#kuroba_close')) {
		kuroba_close_modal();
		return;
	}

	const goto_btn = target.closest('.kuroba_goto_btn');
	if (goto_btn) {
		kuroba_close_modal();
		if (goto_btn.dataset.thread) {
			window.location = `/${kuroba_get_board()}/thread/${goto_btn.dataset.thread}#p${goto_btn.dataset.num}`;
			return;
		}
		kuroba_goto_post(parseInt(goto_btn.dataset.num, 10));
		return;
	}

	if (target.id === 'kuroba_overlay') {
		kuroba_close_modal();
		return;
	}
}

function kuroba_doc_keydown(event) {
	const settings_modal = document.getElementById('settings_modal');
	if (settings_modal && settings_modal.style.display === 'block') {
		return;
	}

	if (document.getElementById('viewer')) {
		return;
	}

	if (document.getElementById('kuroba_overlay') && event.key === 'Escape') {
		kuroba_close_modal();
	}
}

function kuroba_init() {
	if (!kurobaex_mode_active()) {
		return;
	}

	for (const backlink_div of doc_query_all('.backlink')) {
		const num = parseInt(backlink_div.id.replace('bl_', ''), 10);
		if (isNaN(num)) {
			continue;
		}
		backlink_div.classList.add('kuroba_hidden');
		backlink_div.insertAdjacentElement('afterend', kuroba_make_replies_btn(num));
	}

	document.addEventListener('click', kuroba_doc_click);
	document.addEventListener('keydown', kuroba_doc_keydown);
}

kuroba_init();
