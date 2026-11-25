const CATALOG_SEARCH_DEBOUNCE = 400;

let catalog_search_input = null;
let catalog_search_clear_btn = null;
let catalog_search_go_btn = null;
let catalog_search_go_wrap = null;
let catalog_search_board = '';
let catalog_search_debounce_timer = null;

function get_catalog_search_text(card) {
	const title = card.querySelector('.post_title');
	const teaser = card.querySelector('.teaser');
	return ((title ? title.textContent : '') + ' ' + (teaser ? teaser.textContent : '')).toLowerCase();
}

function apply_catalog_filter(query) {
	const threads = document.getElementById('catalog_threads');
	if (!threads) { return; }
	const needle = query.trim().toLowerCase();
	for (const card of threads.children) {
		card.style.display = (!needle || get_catalog_search_text(card).includes(needle)) ? '' : 'none';
	}
}

function build_catalog_search_href(text, board) {
	const endpoint = document.body.dataset.searchEndpoint;
	if (!endpoint) { return ''; }
	if (!text) { return endpoint; }
	const params = new URLSearchParams({boards: board, comment: text});
	return `${endpoint}?${params}`;
}

function update_catalog_search_href() {
	const href = build_catalog_search_href(catalog_search_input.value.trim(), catalog_search_board);
	catalog_search_go_wrap.hidden = !href;
	catalog_search_go_btn.href = href;
}

function apply_catalog_search_filter() {
	apply_catalog_filter(catalog_search_input.value);
	update_catalog_search_href();
}

function debounce_catalog_search() {
	if (catalog_search_debounce_timer !== null) {
		clearTimeout(catalog_search_debounce_timer);
	}
	catalog_search_debounce_timer = setTimeout(apply_catalog_search_filter, CATALOG_SEARCH_DEBOUNCE);
}

function clear_catalog_search() {
	if (catalog_search_debounce_timer !== null) {
		clearTimeout(catalog_search_debounce_timer);
		catalog_search_debounce_timer = null;
	}
	catalog_search_input.value = '';
	apply_catalog_filter('');
	update_catalog_search_href();
	catalog_search_input.focus();
}

function init_catalog_search() {
	const bar = document.getElementById('catalog_search_bar');
	catalog_search_input = document.getElementById('catalog_search_input');
	catalog_search_clear_btn = document.getElementById('catalog_search_clear');
	catalog_search_go_btn = document.getElementById('catalog_search_go');
	catalog_search_go_wrap = document.getElementById('catalog_search_go_wrap');
	if (!bar || !catalog_search_input || !catalog_search_go_btn || !catalog_search_go_wrap) { return; }

	catalog_search_board = get_data_string(bar, 'board');

	catalog_search_input.addEventListener('input', debounce_catalog_search);

	if (catalog_search_clear_btn) {
		catalog_search_clear_btn.addEventListener('click', clear_catalog_search);
	}

	update_catalog_search_href();
}

init_catalog_search();
