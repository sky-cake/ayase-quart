function remove_overlay_image() {
    const cloned_img = document.getElementById('img_cloned');
    if (cloned_img) {
        cloned_img.remove();
    }
}

function ext_is_video(ext) {
    return ["webm","mp4","ogg","mov"].includes(ext?.toLowerCase());
}

function get_video_mimetype(ext) {
    const m = {webm:"video/webm",mp4:"video/mp4",ogg:"video/ogg",mov:"video/quicktime"};
    return m[ext?.toLowerCase()] || "video/webm";
}

function check_all_boards() {
    const checkboxes = doc_query_all('#searchform input[name="boards"][type="checkbox"]');
    for (const checkbox of checkboxes) {
        checkbox.checked = true;
    }
}

function uncheck_all_boards() {
    const checkboxes = doc_query_all('#searchform input[name="boards"][type="checkbox"]');
    for (const checkbox of checkboxes) {
        checkbox.checked = false;
    }
}

function set_up_board_buttons() {
    const all_btn = doc_query_all('.check_all_boards');
    const none_btn = doc_query_all('.uncheck_all_boards');

    if (all_btn.length) {
        all_btn[0].addEventListener('click', check_all_boards);
    }

    if (none_btn.length) {
        none_btn[0].addEventListener('click', uncheck_all_boards);
    }
}

function update_datetimes(root) {
    const datetime_els = (root || document).querySelectorAll('.dateTime');
    const now = new Date();
    for (const datetime_el of datetime_els) {
        const data_utc = get_data_integer(datetime_el, 'utc');
        if (!data_utc) continue;

        const formattedString = format_timestamp(data_utc, now);
        if (!formattedString) {
            datetime_el.textContent = '';
            datetime_el.style.display = 'none';
            continue;
        }
        datetime_el.style.display = '';
        datetime_el.innerHTML = formattedString;
    }
}

function mark_broken_media(img) {
    const media_cont = img.closest('.media_cont');
    if (!media_cont || media_cont.classList.contains('img_broken')) return;
    if (!media_cont.closest('#catalog_threads')) {
        const w = img.clientWidth;
        const h = img.clientHeight;
        if (w > 0 && h > 0) {
            media_cont.style.width = `${w}px`;
            media_cont.style.height = `${h}px`;
            media_cont.classList.add('img_broken_sized');
        }
    }
    media_cont.classList.add('img_broken');
}

function handle_broken_media_error(e) {
    const img = e.target;
    if (img instanceof HTMLImageElement && img.closest('.media_cont')) {
        mark_broken_media(img);
    }
}

window.addEventListener('error', handle_broken_media_error, true);

function mark_already_broken_media() {
    for (const img of doc_query_all('.media_cont img')) {
        if (img.complete && img.naturalWidth === 0) {
            mark_broken_media(img);
        }
    }
}

function update_top_pill_visibility() {
    const top = document.getElementById('top');
    if (!top) return;

    const form = document.getElementById('searchform');
    if (window.matchMedia('(min-width: 901px)').matches || !form) {
        top.classList.add('visible');
        return;
    }

    const results = document.getElementById('resulttop');
    const has_results = results && results.querySelector('.board, .gallery-grid');
    if (!has_results) {
        top.classList.remove('visible');
        return;
    }
    top.classList.toggle('visible', form.getBoundingClientRect().bottom <= 0);
}

function setup_top_pill() {
    const top = document.getElementById('top');
    if (!top) return;

    update_top_pill_visibility();
    window.addEventListener('scroll', update_top_pill_visibility, { passive: true });
    window.addEventListener('resize', update_top_pill_visibility);
}

function init_index() {
	update_datetimes();
    set_up_board_buttons();
    setup_top_pill();
    mark_already_broken_media();
}

init_index();
