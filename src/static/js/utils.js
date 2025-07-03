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
 * @param {string} ancestor_selector css selector for child element
 * @param {string} attr data attribute without 'data-' prefix
 * @returns {number} number or null
 */
function get_ancestor_data_int(elem, ancestor_selector, attr) {
	const ancestor = elem.closest(ancestor_selector);
	if (!ancestor) { return null; }
	return get_data_int(ancestor, attr);
}
