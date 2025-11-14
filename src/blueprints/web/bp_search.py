from time import perf_counter

from quart import flash

from configs import app_conf, index_search_conf, vanilla_search_conf, SITE_NAME
from forms import SearchFormFTS, SearchForm, SearchFormSQL
from moderation import fc
from posts.comments import html_comment, html_highlight
from posts.template_optimizer import (
    get_media_img_t,
    render_wrapped_post_t,
    wrap_post_t
)
from search import get_posts_and_total_hits_fts, get_posts_and_total_hits_sql
from search.pagination import template_pagination_links, total_pages
from templates import template_search
from utils import Perf
from plugins.i_search import search_plugins, intersect_search_plugin_results, SearchPlugin
from jinja2 import Template
from quart_wtf import QuartForm
from moderation.report import generate_report_form


class SearchHandler:
    form: SearchForm
    form_title: str = SITE_NAME
    html_search_memo: str
    html_message_error: str
    enabled: bool
    multi_board_search: bool
    highlight: bool
    board_2_nums: dict[str, set[int]] = dict()

    @property
    def is_gallery_mode(self) -> bool:
        return self.form.gallery_mode.data

    @property
    def is_search_request(self) -> bool:
        return bool(self.form.boards.data)

    @property
    def form_data(self) -> dict:
        form_data = self.form.data
        if self.board_2_nums:
            form_data['board_2_nums'] = self.board_2_nums
        return form_data

    async def get_posts_and_total_hits(self):
        raise NotImplementedError

    def get_posts_t(self, posts: list[dict]):
        posts_t = []
        if not self.is_gallery_mode:
            for post in posts:

                post['comment'] = html_comment(post['comment'], post['thread_num'], post['board_shortname'])

                if self.highlight:
                    hl_search_term_comment = self.form.comment.data if self.form.comment.data else None
                    hl_search_term_title = self.form.title.data if self.form.title.data else None
                    post['comment'] = html_highlight(post['comment'], hl_search_term_comment)
                    post['title'] = html_highlight(post['title'], hl_search_term_title)

                posts_t.append(wrap_post_t(post))

            posts_t = ''.join(render_wrapped_post_t(p) for p in posts_t)

        else:
            # doesn't require restored comments because it's just a gallery
            posts_t = ''.join(get_media_img_t(post, is_search=True) for post in posts)
        return posts_t

    async def filter_posts_and_total_hits(self, posts: list[dict], total_hits: int, logged_in: bool=False):
        post_count_i = len(posts)
        posts = await fc.filter_reported_posts(posts, is_authority=logged_in)
        post_count_f = len(posts)
        total_hits = total_hits - (post_count_i - post_count_f)
        return posts, total_hits


class SearchHandlerSQL(SearchHandler):
    form = SearchFormSQL
    form_title = f'{SITE_NAME} SQL Search'
    enabled: bool = vanilla_search_conf['enabled']
    multi_board_search: bool = vanilla_search_conf['multi_board_search']
    highlight: bool = vanilla_search_conf['highlight']
    html_search_memo = 'SQL search will always yield existing results, but it is slower than index search. Results are exact matching.'
    html_message_error: str = 'There seems to be a problem with the submitted query.'

    async def get_posts_and_total_hits(self):
        return await get_posts_and_total_hits_sql(self.form_data)


class SearchHandlerFTS(SearchHandler):
    form = SearchFormFTS
    form_title = f'{SITE_NAME} Full Text Search'
    enabled: bool = index_search_conf['enabled']
    multi_board_search: bool = index_search_conf['multi_board_search']
    highlight: bool = index_search_conf['highlight']
    html_search_memo = """
    <div class="mtb-1">Full text search is much faster than SQL search, but it may not have recent data.</div>
    <button class="form_btn pbtn" data-toggle="fts_info">Syntax ⓘ</button>
    <div id="fts_info" class="mtb-1 hidden">
        These are the main search operations, more can be found at <a href="https://docs.rs/tantivy/0.19.2/tantivy/query/struct.QueryParser.html" target="_blank">docs.rs/tantivy</a>.
        <ul class="m-0 liststyle">
            <li><span class="codetext">"exact term"</span></li>
            <li><span class="codetext">+devices +usb-c -adapter</span> requires posts with "devices" and "usb-c", and not "adapter"</li>
            <li><span class="codetext">x AND y OR z</span> which is equivalent to <span class="codetext">((+x +y) z)</span></li>
        </ul>
    </div>
    """
    html_message_error: str = (
        'There seems to be a problem with the submitted query.<br>'
        '- Characters like \" and \' should come in pairs.<br>'
        '- Brackets should be paired too.<br>'
        '- You can escape special characters with \\ if needed.<br>'
        '- Also note that you cannot begin or end queries with a dash.'
    )

    async def get_posts_and_total_hits(self):
        return await get_posts_and_total_hits_fts(self.form_data)


def bind_plugin_fields_to_form(form: QuartForm, search_plugins: dict[str, SearchPlugin], plugin_templates: list[Template]):
    """Call before form instantiation."""
    for plugin_name, plugin in search_plugins.items():
        plugin_templates.append(plugin.template)
        for field in plugin.fields:
            setattr(form, field.name, field)


async def search_handler(handler: SearchHandler, request_args: dict, endpoint_path: str, logged_in=False, is_admin=False) -> str:
    p = Perf(f'{handler.form_title} search', enabled=app_conf.get('testing'))

    plugin_templates: list[Template] = []
    if search_plugins:
        bind_plugin_fields_to_form(handler.form, search_plugins, plugin_templates)

    # turn off csrf so search result links can be shared
    handler.form = await handler.form.create_form(meta={'csrf': False}, data=request_args)

    did_any_search = False
    posts_t = []
    posts = []
    total_hits = 0
    cur_page = 1
    page_links = ''
    quotelinks = []

    if handler.is_search_request and (await handler.form.validate()):
        do_native_search = True
        did_plugin_search = False

        time_search_start = perf_counter()

        if search_plugins:
            result = await intersect_search_plugin_results(search_plugins, handler.form, p)

            if result.performed_search:
                did_plugin_search = True
                did_any_search = True

                if result.flash_msg:
                    await flash(result.flash_msg)

                if result.board_2_nums:
                    handler.board_2_nums = result.board_2_nums
                else:
                    # no results found from plugin search -> no native search results
                    do_native_search = False
                    time_search_end = perf_counter()

        if do_native_search:
            did_any_search = True
            if app_conf.get('testing'):
                # show the real errors
                posts, total_hits = await handler.get_posts_and_total_hits()
            else:
                try:
                    posts, total_hits = await handler.get_posts_and_total_hits()
                except Exception:
                    msg = handler.html_message_error
                    await flash(msg)

            time_search_end = perf_counter()
            p.check('search done')

            posts, total_hits = await handler.filter_posts_and_total_hits(posts, total_hits, logged_in=logged_in)
            p.check('filter_reported')

            posts_t = handler.get_posts_t(posts)
            p.check('templated posts')

            if did_plugin_search:
                # Plugin search gets no paging due to the nature of "post-filtering". See AQ plugin docs.
                total_hits = min(total_hits, handler.form.hits_per_page.data)
                # if total_hits == handler.form.hits_per_page.data:
                #     await flash('- Max page size reached. Note that AQ does not perform pagination with search plugins. To find other results, specify other query arguments.')
            else:
                page_count = total_pages(total_hits, handler.form.hits_per_page.data)
                page_links = template_pagination_links(endpoint_path, handler.form.data, page_count, section='resulttop')
                p.check('templated links')

        cur_page = handler.form.page.data or cur_page

    yield_message = ''
    if did_any_search:
        yield_message = f'Searched archive in {time_search_end-time_search_start:,.3f}s. Post search hits: {total_hits:,}'

    search_plugin_html = ''
    for plugin_template in plugin_templates:
        search_plugin_html += plugin_template.render(form=handler.form)

    rendered_page = template_search.render(
        html_search_memo=handler.html_search_memo,
        yield_message=yield_message,
        gallery_mode=handler.is_gallery_mode,
        form=handler.form,
        search_plugin_html=search_plugin_html,
        posts_t=posts_t,
        page_links=page_links,
        page_post_count=len(posts),
        searched=did_any_search,
        quotelinks=quotelinks,
        title=handler.form_title,
        cur_page=cur_page,
        total_hits=f'{total_hits:,}' if total_hits else 0,
        logged_in=logged_in,
        is_admin=is_admin,
        report_form_t=generate_report_form(),
    )

    p.check('rendered page')
    print(p)

    return rendered_page
