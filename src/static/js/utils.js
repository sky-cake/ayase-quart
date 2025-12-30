/**
 * Extract data-int-property as number
 * @param {Element} elem dom element
 * @param {string} attr data attribute without 'data-' prefix
 * @returns {number} number or null
 */
function get_data_integer(elem, attr) {
	const integer = parseInt(elem.dataset[attr].trim(), 10);
	return isNaN(integer) ? null : integer;
}

/**
 * Extract data-str-property as trimmed string
 * @param {Element} elem dom element
 * @param {string} attr data attribute without 'data-' prefix
 * @returns {string} string or null
 */
function get_data_string(elem, attr) {
	const value = elem.dataset[attr];
	return value !== undefined ? value.trim() : null;
}

/**
 * Get child element containing a data attribute
 * @param {Element} elem dom element
 * @param {string} attr data attribute without 'data-' prefix
 * @returns {Element} element or null
 */
function get_data_elem(elem, attr) {
	return elem.querySelector(`[data-${attr}]`);
}

/**
 * Get all child elements containing a data attribute
 * @param {Element} elem dom element
 * @param {string} attr data attribute without 'data-' prefix
 * @returns {NodeListOf<Element>} nodelist of HTMLElement
 */
function get_data_elem_all(elem, attr) {
	return elem.querySelectorAll(`[data-${attr}]`);
}

/**
 * Shorthand document.querySelectorAll
 * @param {string} selector css selector for querySelectorAll
 * @returns {NodeListOf<HTMLElement>} nodelist of HTMLElement
 */
function doc_query_all(selector) {
	return document.querySelectorAll(selector);
}

/**
 * Safely attach native event handler to child node
 * Will not attach anything if child does not exist
 * Returns child element if found, otherwise null
 * @param {Element} parent_elem parent element to query
 * @param {string} child_selector css selector for child element
 * @param {string} event native event ('click', 'mouseover', etc...)
 * @param {function} callback_fn event handler callback function
 * @returns {Element} element or null
 */
function add_child_event(parent_elem, child_selector, event, callback_fn) {
	const element = parent_elem.querySelector(child_selector);
	if (!element) { return null; }
	element.addEventListener(event, callback_fn);
	return element;
}

/**
 * Attempt to extract data-int-property as number from parent element
 * @param {Element} elem dom element
 * @param {string} ancestor_selector css selector to find ancestor element
 * @param {string} attr data attribute without 'data-' prefix
 * @returns {number} number or null
 */
function get_ancestor_data_int(elem, ancestor_selector, attr) {
	const ancestor = elem.closest(ancestor_selector);
	if (!ancestor) { return null; }
	return get_data_int(ancestor, attr);
}

const locale_ts_opts = {
	year: 'numeric',
	month: 'short',
	day: 'numeric',
	hour: '2-digit',
	minute: '2-digit',
	timeZoneName: 'short',
};

function plural_past(val) {
	return val > 1 ? `s ago` : ' ago';
}

/**
 * Render utc unix timestamp to client locale + relative humanized
 * @param {number} ts utc unix timestamp
 * @param {Date|undefined} now optional Date() object when calculating many
 * @param {Boolean|undefined} relative_time_nl Put (N <unit of time> ago) on a new line?
 * @returns {string} formatted timestamp
 */
function format_timestamp(ts, now=undefined, relative_time_nl=false) {
    const postDate = new Date(ts * 1000);
    const _now = now ?? new Date();
    const delta = _now - postDate;
    
    const formatted_ts = postDate.toLocaleString(undefined, locale_ts_opts);
    
    const seconds = Math.floor(delta / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const months = Math.floor(days / 30);
    const years = Math.floor(days / 365);
    
    let relative_time = 'now';
    if (years) {
        relative_time = `${years} year${plural_past(years)}`;
    } else if (months) {
        relative_time = `${months} month${plural_past(months)}`;
    } else if (days) {
        relative_time = `${days} day${plural_past(days)}`;
    } else if (hours) {
        relative_time = `${hours} hour${plural_past(hours)}`;
    } else if (minutes) {
        relative_time = `${minutes} min${plural_past(minutes)}`;
    } else if (seconds) {
        relative_time = `${seconds} sec${plural_past(seconds)}`;
    }

	let sep = ' ';
	if (relative_time_nl) sep = '<br>'
    
    return `${formatted_ts}${sep}(${relative_time})`;
}

const video_extensions = new Map([
	['mp4', 'video/mp4'],
	['webm', 'video/webm'],
]);
const image_extensions = new Set([
	'jpg',
	'jpeg',
	'png',
	'bmp',
	'gif',
	'webp',
]);

/**
 * Determine if file extension is for video files
 * @param {string} ext file extension
 * @returns {bool} true if extension is used for videos
 */
function ext_is_video(ext) {
	return video_extensions.has(ext);
}

/**
 * Get the mime type of a video extension
 * @param {string} ext file extension
 * @returns {string} mimetype if found or empty string
 */
function get_video_mimetype(ext) {
	return video_extensions.get(ext) ?? '';
}

/**
 * Determine if file extension is for image files
 * @param {string} ext file extension
 * @returns {bool} true if extension is used for images
 */
function ext_is_image(ext) {
	return image_extensions.has(ext);
}
