const SETTINGS_KEY = 'aq_settings';

const DEFAULT_SETTINGS = {
	font_size: 10,
	display_relative_time: true,
	display_time: true,
	show_datetime: true,
};

function get_settings() {
	try {
		const stored = JSON.parse(localStorage.getItem(SETTINGS_KEY));
		return Object.assign({}, DEFAULT_SETTINGS, stored || {});
	} catch (e) {
		return Object.assign({}, DEFAULT_SETTINGS);
	}
}

function save_settings(settings) {
	localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

function apply_settings() {
	const settings = get_settings();
	document.body.style.fontSize = `${settings.font_size}pt`;
}

function close_settings_modal() {
	const overlay = document.getElementById('settings_overlay');
	const modal = document.getElementById('settings_modal');
	if (overlay) overlay.style.display = 'none';
	if (modal) modal.style.display = 'none';
}

function update_display_time_state() {
	const show_datetime = document.getElementById('settings_show_datetime');
	const display_time = document.getElementById('settings_display_time');
	const disabled = !show_datetime.checked;
	display_time.disabled = disabled;
	display_time.closest('.settings_field').classList.toggle('disabled', disabled);
}

function open_settings_modal() {
	const settings = get_settings();
	document.getElementById('settings_font_size').value = settings.font_size;
	document.getElementById('settings_relative_time').checked = settings.display_relative_time;
	document.getElementById('settings_display_time').checked = settings.display_time;
	document.getElementById('settings_show_datetime').checked = settings.show_datetime;
	update_display_time_state();
	document.getElementById('settings_overlay').style.display = 'block';
	document.getElementById('settings_modal').style.display = 'block';
}

function save_settings_modal() {
	const font_size = parseInt(document.getElementById('settings_font_size').value, 10);
	save_settings({
		font_size: Number.isNaN(font_size) ? DEFAULT_SETTINGS.font_size : font_size,
		display_relative_time: document.getElementById('settings_relative_time').checked,
		display_time: document.getElementById('settings_display_time').checked,
		show_datetime: document.getElementById('settings_show_datetime').checked,
	});
	apply_settings();
	if (typeof update_datetimes === 'function') { update_datetimes(); }
	close_settings_modal();
}

function open_settings_via_click(event) {
	event.preventDefault();
	open_settings_modal();
}

function close_settings_via_overlay_click(event) {
	if (event.target === event.currentTarget) {
		close_settings_modal();
	}
}

function handle_settings_keydown(event) {
	if (event.key === 'Escape') {
		close_settings_modal();
	}
	const modal = document.getElementById('settings_modal');
	if (event.key === 'Enter' && modal.style.display === 'block') {
		event.preventDefault();
		save_settings_modal();
	}
}

function init_settings() {
	const open_button = document.getElementById('settings_open');
	const overlay = document.getElementById('settings_overlay');
	const modal = document.getElementById('settings_modal');

	if (!open_button || !overlay || !modal) { return; }

	open_button.addEventListener('click', open_settings_via_click);

	document.getElementById('settings_close').addEventListener('click', close_settings_modal);

	document.getElementById('settings_show_datetime').addEventListener('change', update_display_time_state);

	overlay.addEventListener('click', close_settings_via_overlay_click);

	document.addEventListener('keydown', handle_settings_keydown);

	document.getElementById('settings_save').addEventListener('click', save_settings_modal);
}

apply_settings();
init_settings();
