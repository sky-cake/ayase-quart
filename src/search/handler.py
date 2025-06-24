from quart import flash, redirect, request, url_for, current_app
from werkzeug.exceptions import BadRequest, MethodNotAllowed

from configs import (
    SITE_NAME,
    app_conf,
    index_search_conf,
    tag_conf,
    vanilla_search_conf
)
from enums import SearchType
from forms import IndexSearchForm, SearchForm, VanillaSearchForm
from moderation.filter_cache import fc
from posts.comments import html_comment, html_highlight
from posts.template_optimizer import (
    get_media_img_t,
    render_wrapped_post_t,
    report_modal_t,
    wrap_post_t
)
from search.pagination import template_pagination_links, total_pages
from tagging.enums import SafeSearch
from templates import template_search
from utils import Perf
from search import get_posts_and_total_hits, search_w_file
from werkzeug.datastructures import FileStorage
from time import perf_counter
from tagging.db import get_image_count


toggle_fts_info_html = """
  <div class="mtb-1">Full text search is much faster than SQL search, but it may not have recent data.</div>
  <button class="form_btn pbtn" data-toggle="fts_info">Syntax ⓘ</button>
  <div id="fts_info" class="mtb-1" style="display: none;">
    These are the main search operations, more can be found at <a href="https://docs.rs/tantivy/0.19.2/tantivy/query/struct.QueryParser.html" target="_blank">docs.rs/tantivy</a>.
    <ul class="m-0 liststyle">
        <li><span class="codetext">"exact term"</span></li>
        <li><span class="codetext">+devices +usb-c -adapter</span> requires posts with "devices" and "usb-c", and not "adapter"</li>
        <li><span class="codetext">x AND y OR z</span> which is equivalent to <span class="codetext">((+x +y) z)</span></li>
    </ul>
  </div>
"""

async def search_handler(search_type: SearchType, logged_in=False, is_admin=False) -> str:
    if request.method not in ['GET', 'POST']:
        raise MethodNotAllowed

    if search_type == SearchType.idx:
        search_conf = index_search_conf
        search_form = IndexSearchForm
        search_type_message = toggle_fts_info_html
    elif search_type == SearchType.sql:
        search_conf = vanilla_search_conf
        search_form = VanillaSearchForm
        search_type_message = 'SQL search will always yield existing results, but it is slower than index search. Results are exact matching.'
    else:
        raise BadRequest('unknown search type')

    if not search_conf['enabled']:
        raise BadRequest('search type disabled')

    gallery_mode = False
    searched = False
    cur_page = 1
    total_hits = None
    posts_t = []
    posts = []
    quotelinks = []
    page_links = ''
    file_image = None

    p = Perf(f'{search_type.value} search', enabled=app_conf.get('testing'))

    if request.method == 'GET':
        params = {**request.args}
        params['boards'] = request.args.get('boards')

    elif request.method == 'POST':
        formdata = await request.form
        params = {**formdata}
        params['boards'] = formdata.get('boards')

        files = await request.files
        file_image: FileStorage = files.get('file_upload')

    if params['boards']:
        params['boards'] = params['boards'].split(',')

        if not search_conf['multi_board_search']:
            params['boards'] = [params['boards'][0]]

    current_app.logger.error(f"{type(params['boards'])}  {params['boards']}")
    form: SearchForm = await search_form.create_form(meta={'csrf': False}, **params)
    current_app.logger.error(f"{type(params['boards'])}  {params['boards']}  {type(form.boards.data)}  {form.boards.data}")

    is_search_request = bool(form.boards.data)

    if is_search_request and (await form.validate()):
        searched = True
        if form.gallery_mode.data:
            gallery_mode = True

        form_data = form.data

        posts = []
        total_hits = 0
        t1 = perf_counter()

        is_tag_search = False
        if tag_conf['enabled'] and bool(form_data['file_tags_general'] or form_data['file_tags_character']):
            if SafeSearch(int(form_data['safe_search'])) == SafeSearch.unsafe:
                return redirect(url_for('bp_web_about.soy'))

            is_tag_search = True
            form_data['has_file'] = True

            # converted from '1,2,3,4,5' -> [1,2,3,4,5] by src/forms/__init__.py handling
            tag_ids = form_data.get('file_tags_general', []) + form_data.get('file_tags_character', [])
            form_data['tag_ids'] = tag_ids
            posts, total_hits = await get_posts_and_total_hits(search_type, form_data)

            p.check('tag search done')

        is_file_search = False
        if tag_conf['enabled'] and tag_conf['allow_file_search'] and file_image:
            d = await search_w_file(form_data, file_image, search_type)
            posts, total_hits = d['posts'], d['total_hits']

            is_file_search = True
            form_data['has_file'] = True

            p.check('file search done')

        if not posts and not is_tag_search and not is_file_search:
            try:
                posts, total_hits = await get_posts_and_total_hits(search_type, form_data)
            except Exception as e:
                msg = (
                    'There seems to be a problem with the submitted query.<br>'
                    '- Characters like \" and \' should come in pairs.<br>'
                    '- Brackets should be paired too.<br>'
                    '- You can escape special characters with \\ if needed.<br>'
                    '- Also note that you cannot begin or end queries with a dash.'
                )
                if app_conf.get('testing'):
                    msg += '<br><br>' + str(e)

                await flash(msg)
                posts, total_hits = [], 0

        t2 = perf_counter()
        p.check('search done')

        post_count_i = len(posts)
        posts = await fc.filter_reported_posts(posts)
        post_count_f = len(posts)
        total_hits = total_hits - (post_count_i - post_count_f)

        p.check('filter_reported')

        if not gallery_mode:
            for post in posts:

                post['comment'] = html_comment(post['comment'], post['thread_num'], post['board_shortname'])

                if search_conf['highlight']:
                    hl_search_term_comment = form.comment.data if form.comment.data else None
                    hl_search_term_title = form.title.data if form.title.data else None
                    post['comment'] = html_highlight(post['comment'], hl_search_term_comment)
                    post['title'] = html_highlight(post['title'], hl_search_term_title)

                posts_t.append(wrap_post_t(post))

            posts_t = ''.join(render_wrapped_post_t(p) for p in posts_t)

        else:
            # doesn't require restored comments because it's just a gallery
            posts_t = ''.join(get_media_img_t(post, is_search=True) for post in posts)

        p.check('templated posts')

        # revert these back to csv before pagination links
        # tag_ids is not used by the UI
        form.file_tags_general.data = ','.join([str(s) for s in form_data['file_tags_general']])
        form.file_tags_character.data = ','.join([str(s) for s in form_data['file_tags_character']])
        form_data['file_tags_general'] = form.file_tags_general.data
        form_data['file_tags_character'] = form.file_tags_character.data
        form_data.pop('tag_ids', None)

        endpoint_path = url_for('bp_web_index_search.v_index_search_get') if search_type == SearchType.idx else url_for('bp_web_vanilla_search.v_vanilla_search_get')
        page_count = total_pages(total_hits, form_data['hits_per_page'])
        page_links = template_pagination_links(endpoint_path, form_data, page_count, section='resulttop')

        p.check('templated links')
        cur_page = form_data.get('page', cur_page)

        form.boards.data = form.boards.data if search_conf['multi_board_search'] else form.boards.data[0]

    yield_message = ''
    if searched:
        if is_tag_search:
            image_count = await get_image_count()
            yield_message = f'{image_count:,} images searched in {t2-t1:,.3f}s. Tag search hits: {total_hits}'
        elif is_file_search:
            yield_message = f'Searched archive in {t2-t1:,.3f}s. ' + d['message'] + '<br>' + d['api_response']
        else:
            yield_message = f'Searched archive in {t2-t1:,.3f}s. Post search hits: {total_hits:,}'

    rendered_page = template_search.render(
        search_type_message=search_type_message,
        yield_message=yield_message,
        gallery_mode=gallery_mode,
        form=form,
        posts_t=posts_t,
        report_modal_t=report_modal_t,
        page_links=page_links,
        page_post_count=len(posts),
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=SITE_NAME,
        title='Ayase Quart ' + ('Full Text Search' if search_type == SearchType.idx else 'SQL Search'),
        cur_page=cur_page,
        total_hits=f'{total_hits:,}' if total_hits else 0,
        logged_in=logged_in,
        is_admin=is_admin,
    )

    p.check('rendered page')
    print(p)

    return rendered_page
