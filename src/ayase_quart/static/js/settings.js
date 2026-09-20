const SETTINGS_KEY = 'aq_settings';

const DEFAULT_SETTINGS = {
	font_size: 12,
	display_relative_time: true,
	display_time: true,
	show_datetime: true,
	kurobaex_mode: true,
	thumb_size: 150,
	show_media_hover: true,
	autoplay_videos: true,
	mute_videos: false,
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
	document.documentElement.style.setProperty('--thumb-size', `${settings.thumb_size}px`);
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
	document.getElementById('settings_thumb_size').value = settings.thumb_size;
	document.getElementById('settings_relative_time').checked = settings.display_relative_time;
	document.getElementById('settings_display_time').checked = settings.display_time;
	document.getElementById('settings_show_datetime').checked = settings.show_datetime;
	document.getElementById('settings_kurobaex_mode').checked = settings.kurobaex_mode;
	document.getElementById('settings_show_media_hover').checked = settings.show_media_hover;
	document.getElementById('settings_autoplay_videos').checked = settings.autoplay_videos;
	document.getElementById('settings_mute_videos').checked = settings.mute_videos;
	update_display_time_state();
	document.getElementById('settings_overlay').style.display = 'block';
	document.getElementById('settings_modal').style.display = 'block';
}

function save_settings_modal() {
	const font_size = parseInt(document.getElementById('settings_font_size').value, 10);
	const thumb_size = parseInt(document.getElementById('settings_thumb_size').value, 10);
	const previous = get_settings();
	const settings = {
		font_size: Number.isNaN(font_size) ? DEFAULT_SETTINGS.font_size : font_size,
		thumb_size: Number.isNaN(thumb_size) ? DEFAULT_SETTINGS.thumb_size : thumb_size,
		display_relative_time: document.getElementById('settings_relative_time').checked,
		display_time: document.getElementById('settings_display_time').checked,
		show_datetime: document.getElementById('settings_show_datetime').checked,
		kurobaex_mode: document.getElementById('settings_kurobaex_mode').checked,
		show_media_hover: document.getElementById('settings_show_media_hover').checked,
		autoplay_videos: document.getElementById('settings_autoplay_videos').checked,
		mute_videos: document.getElementById('settings_mute_videos').checked,
	};
	save_settings(settings);
	apply_settings();
	if (typeof update_datetimes === 'function') { update_datetimes(); }
	if (settings.kurobaex_mode !== previous.kurobaex_mode) {
		location.reload();
		return;
	}
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
