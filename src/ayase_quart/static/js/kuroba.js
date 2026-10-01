let kuroba_view_stack = [];
const kuroba_post_cache = new Map();
const kuroba_post_fetching = new Set();
const kuroba_replies_cache = new Map();
const kuroba_replies_fetching = new Set();

function kuroba_num_from_quotelink(quotelink) {
	return parseInt(quotelink.getAttribute('href').split('#p')[1], 10);
}

function kuroba_is_thread_page(board) {
	return location.pathname.startsWith(`/${board}/thread/`);
}

function kuroba_post_container(num, board) {
	return document.querySelector(`#pc${num}[data-board="${board}"]`);
}

function kuroba_get_reply_nums(num, board) {
	const nums = [];
	const backlink_div = document.querySelector(`#bl_${num}[data-board="${board}"]`);
	if (!backlink_div) {
		return nums;
	}
	for (const link of backlink_div.querySelectorAll('a.quotelink')) {
		const reply_num = kuroba_num_from_quotelink(link);
		if (!nums.includes(reply_num)) {
			nums.push(reply_num);
		}
	}
	return nums;
}

function kuroba_make_replies_btn(num, board, nums) {
	const btn = document.createElement('button');
	btn.type = 'button';
	btn.classList.add('kuroba_replies_btn');
	btn.classList.add('btn');
	btn.dataset.num = String(num);
	btn.dataset.board = board;
	btn.dataset.nums = nums.join(',');
	const count = nums.length;
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

function kuroba_highlight_quotelinks(blockquote, highlight_num) {
	if (highlight_num === null) {
		return;
	}
	const links = blockquote.querySelectorAll('a.quotelink');
	if (links.length < 2) {
		return;
	}
	for (const link of links) {
		if (kuroba_num_from_quotelink(link) === highlight_num) {
			link.classList.add('hl_dark');
			break;
		}
	}
}

function kuroba_make_entry_shell(num) {
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
	content.appendChild(header);
	entry.appendChild(content);

	return [entry, content, header];
}

function kuroba_make_goto_btn(entry, num, board, thread_num = null) {
	const goto_btn = document.createElement('button');
	goto_btn.type = 'button';
	goto_btn.classList.add('kuroba_goto_btn');
	goto_btn.classList.add('btn');
	goto_btn.dataset.num = String(num);
	goto_btn.dataset.board = board;
	if (thread_num) {
		goto_btn.dataset.thread = String(thread_num);
	}
	goto_btn.textContent = '→';
	goto_btn.title = 'Go to post';
	entry.appendChild(goto_btn);
}

function kuroba_build_entry(num, board, highlight_num = null) {
	const [entry, content, header] = kuroba_make_entry_shell(num);

	const post_container = kuroba_post_container(num, board);

	const post_info = post_container && post_container.querySelector('#pi' + num);
	if (post_info) {
		const datetime = post_info.querySelector('.dateTime');
		if (datetime) {
			header.appendChild(datetime.cloneNode(true));
		}
	}

	const media_img = post_container && post_container.querySelector('.media_cont img.mtog');
	if (media_img) {
		content.appendChild(kuroba_build_media(media_img));
	}

	const comment = post_container && post_container.querySelector('.postMessage');
	if (comment) {
		const blockquote = comment.cloneNode(false);
		blockquote.removeAttribute('id');
		blockquote.classList.add('kuroba_entry_comment');
		blockquote.innerHTML = comment.innerHTML;
		kuroba_highlight_quotelinks(blockquote, highlight_num);
		content.appendChild(blockquote);
	}

	const nums = kuroba_get_reply_nums(num, board);
	if (nums.length > 0) {
		content.appendChild(kuroba_make_replies_btn(num, board, nums));
	}

	kuroba_make_goto_btn(entry, num, board);

	return entry;
}

function kuroba_post_response_to_json(response) {
	return response.ok ? response.json() : Promise.reject();
}

function kuroba_post_key(board, num) {
	return `${board}:post:${num}`;
}

function kuroba_replies_key(board, num) {
	return `${board}:replies:${num}`;
}

function kuroba_store_post_response(board, num, data) {
	kuroba_post_fetching.delete(kuroba_post_key(board, num));
	if (data && data.html_content) {
		kuroba_post_cache.set(kuroba_post_key(board, num), data);
	} else {
		kuroba_post_cache.set(kuroba_post_key(board, num), {});
	}
	if (document.getElementById('kuroba_overlay')) {
		kuroba_render_modal();
	}
}

function kuroba_store_post_error(board, num) {
	kuroba_post_fetching.delete(kuroba_post_key(board, num));
	kuroba_post_cache.set(kuroba_post_key(board, num), {});
	if (document.getElementById('kuroba_overlay')) {
		kuroba_render_modal();
	}
}

function kuroba_fetch_post(board, num) {
	const post_key = kuroba_post_key(board, num);
	if (kuroba_post_cache.has(post_key) || kuroba_post_fetching.has(post_key)) {
		return;
	}
	kuroba_post_fetching.add(post_key);
	fetch(`/${board}/post/${num}`)
		.then(kuroba_post_response_to_json)
		.then(kuroba_store_post_response.bind(null, board, num))
		.catch(kuroba_store_post_error.bind(null, board, num));
}

function kuroba_store_replies_response(board, num, data) {
	kuroba_replies_fetching.delete(kuroba_replies_key(board, num));
	kuroba_replies_cache.set(kuroba_replies_key(board, num), data || { posts: [], missing: [], capped: false });
	if (document.getElementById('kuroba_overlay')) {
		kuroba_render_modal();
	}
}

function kuroba_store_replies_error(board, num) {
	kuroba_replies_fetching.delete(kuroba_replies_key(board, num));
	kuroba_replies_cache.set(kuroba_replies_key(board, num), { posts: [], missing: [], capped: false });
	if (document.getElementById('kuroba_overlay')) {
		kuroba_render_modal();
	}
}

function kuroba_fetch_replies(board, num, nums) {
	const replies_key = kuroba_replies_key(board, num);
	if (kuroba_replies_cache.has(replies_key) || kuroba_replies_fetching.has(replies_key)) {
		return;
	}
	kuroba_replies_fetching.add(replies_key);
	fetch(`/${board}/posts?nums=${nums.slice(0, 100).join(',')}`)
		.then(kuroba_post_response_to_json)
		.then(kuroba_store_replies_response.bind(null, board, num))
		.catch(kuroba_store_replies_error.bind(null, board, num));
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

function kuroba_build_capped_notice() {
	const div = document.createElement('div');
	div.classList.add('kuroba_empty');
	div.textContent = 'Showing first 100 replies.';
	return div;
}

function kuroba_build_cross_entry(num, board, data, highlight_num = null) {
	const container = document.createElement('div');
	container.innerHTML = data.html_content;
	const post = container.querySelector('.post');

	const [entry, content, header] = kuroba_make_entry_shell(num);

	if (post) {
		const datetime = post.querySelector('.dateTime');
		if (datetime) {
			header.appendChild(datetime.cloneNode(true));
		}

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
			kuroba_highlight_quotelinks(blockquote, highlight_num);
			content.appendChild(blockquote);
		}
	}

	kuroba_make_goto_btn(entry, num, board, data.thread_num || null);

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
	footer.appendChild(back_btn);
	footer.appendChild(close_btn);

	modal.appendChild(body);
	modal.appendChild(footer);
	overlay.appendChild(modal);
	document.body.appendChild(overlay);
	return overlay;
}

function kuroba_render_replies_view(view, body) {
	const nums = kuroba_get_reply_nums(view.num, view.board);
	if (nums.length === 0) {
		const empty = document.createElement('div');
		empty.classList.add('kuroba_empty');
		empty.textContent = 'No replies';
		body.appendChild(empty);
		return;
	}
	for (const num of nums) {
		body.appendChild(kuroba_build_entry(num, view.board, view.num));
	}
}

function kuroba_render_replies_remote_view(view, body) {
	const replies_key = kuroba_replies_key(view.board, view.num);
	const data = kuroba_replies_cache.get(replies_key);
	if (!data) {
		body.appendChild(kuroba_build_loading());
		kuroba_fetch_replies(view.board, view.num, view.nums);
		return;
	}

	if (data.capped || view.nums_capped) {
		body.appendChild(kuroba_build_capped_notice());
	}

	for (const post of data.posts) {
		body.appendChild(kuroba_build_cross_entry(post.num, view.board, post, view.num));
	}

	for (const num of data.missing) {
		body.appendChild(kuroba_build_not_found());
	}

	if (data.posts.length === 0 && data.missing.length === 0 && !data.capped) {
		const empty = document.createElement('div');
		empty.classList.add('kuroba_empty');
		empty.textContent = 'No replies';
		body.appendChild(empty);
	}
}

function kuroba_render_modal() {
	kuroba_ensure_modal();
	const view = kuroba_view_stack[kuroba_view_stack.length - 1];

	const body = document.getElementById('kuroba_modal_body');
	body.replaceChildren();

	if (view.type === 'replies') {
		kuroba_render_replies_view(view, body);
	} else if (view.type === 'replies_remote') {
		kuroba_render_replies_remote_view(view, body);
	} else if (view.type === 'cross_post') {
		const data = kuroba_post_cache.get(kuroba_post_key(view.board, view.num));
		if (!data) {
			body.appendChild(kuroba_build_loading());
		} else if (!data.html_content) {
			body.appendChild(kuroba_build_not_found());
		} else {
			body.appendChild(kuroba_build_cross_entry(view.num, view.board, data));
		}
	} else {
		body.appendChild(kuroba_build_entry(view.num, view.board));
	}

	document.getElementById('kuroba_back').disabled = kuroba_view_stack.length <= 1;
	body.scrollTop = 0;
	update_datetimes(body);
}

function kuroba_open_post_view(num, board) {
	if (kuroba_post_container(num, board)) {
		kuroba_view_stack.push({ type: 'post', num: num, board: board });
		kuroba_render_modal();
		viewer_update_scroll_lock();
		return;
	}
	kuroba_view_stack.push({ type: 'cross_post', num: num, board: board });
	kuroba_render_modal();
	viewer_update_scroll_lock();
	kuroba_fetch_post(board, num);
}

function kuroba_open_replies_view(num, board) {
	if (kuroba_is_thread_page(board)) {
		kuroba_view_stack.push({ type: 'replies', num: num, board: board });
	} else {
		// posts aren't rendered on search/index pages, fetch them in one batch
		const nums = kuroba_get_reply_nums(num, board);
		const nums_capped = nums.length > 100;
		kuroba_view_stack.push({ type: 'replies_remote', num: num, board: board, nums: nums, nums_capped: nums_capped });
	}
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

function kuroba_goto_post(num, board) {
	const post = kuroba_post_container(num, board);
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
		if (!quotelink.getAttribute('href')) {
			return;
		}
		event.preventDefault();
		const num = kuroba_num_from_quotelink(quotelink);
		const board = get_data_string(quotelink, 'board');
		if (!board) {
			return;
		}
		kuroba_open_post_view(num, board);
		return;
	}

	const replies_btn = target.closest('.kuroba_replies_btn');
	if (replies_btn) {
		kuroba_open_replies_view(parseInt(replies_btn.dataset.num, 10), replies_btn.dataset.board);
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
			window.location = `/${goto_btn.dataset.board}/thread/${goto_btn.dataset.thread}#p${goto_btn.dataset.num}`;
			return;
		}
		kuroba_goto_post(parseInt(goto_btn.dataset.num, 10), goto_btn.dataset.board);
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
		const board = get_data_string(backlink_div, 'board');
		if (!board) {
			continue;
		}
		backlink_div.classList.add('kuroba_hidden');
		backlink_div.insertAdjacentElement('afterend', kuroba_make_replies_btn(num, board, kuroba_get_reply_nums(num, board)));
	}

	document.addEventListener('click', kuroba_doc_click);
	document.addEventListener('keydown', kuroba_doc_keydown);
}

kuroba_init();
