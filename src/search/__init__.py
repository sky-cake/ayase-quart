from quart import flash

from asagi_converter import search_posts
from configs import index_search_conf, media_conf, vanilla_search_conf
from enums import SearchType
from search.post_metadata import board_2_int
from search.providers import get_index_search_provider
from search.query import IndexSearchQuery, get_index_search_query


async def _get_posts_and_total_hits_fts(form_data: dict) -> tuple[list[dict], int]:
    if not isinstance(form_data['boards'], list):
        raise ValueError(form_data['boards'])

    index_searcher = get_index_search_provider()
    board_ints = [board_2_int(board) for board in form_data['boards']]

    if form_data['op_title'] or form_data['op_comment']:
        q = IndexSearchQuery(
            op=True,
            comment=form_data['op_comment'] if form_data['op_comment'] else None,
            title=form_data['op_title'] if form_data['op_title'] else None,
            boards=board_ints,
            hits_per_page=index_search_conf['max_hits'], # max_hits due to facet search
        )
        boards_2_threadnums, total_threads_hits = await index_searcher.search_posts_get_thread_nums(q)
        posts = []
        total_hits = 0
        for board, thread_nums in boards_2_threadnums.items():
            # must go one board at a time to maintain board:thread_num integrity
            # if we want, we can limit faceted search to 1 board in the form validation
            form_data['boards'] = [board]
            form_data['thread_nums'] = thread_nums
            query = get_index_search_query(form_data)
            _posts, _total_hits = await index_searcher.search_posts(query)
            posts.extend(_posts)
            total_hits += _total_hits
        return posts, total_hits

    query = get_index_search_query(form_data, board_ints=board_ints)
    return await index_searcher.search_posts(query)


async def get_posts_and_total_hits_fts(form_data: dict):
    return await _get_posts_and_total_hits_fts(form_data)


async def get_posts_and_total_hits_sql(form_data: dict):
    return await search_posts(form_data, vanilla_search_conf['max_hits'])


async def get_posts_and_total_hits(search_type: SearchType, form_data: dict) -> tuple[list[dict], int]:
    if not isinstance(form_data['boards'], list):
        raise ValueError(form_data['boards'])

    # do not provide gallery results for boards that have non-served media
    if form_data.get('gallery_mode'):
        b_i = len(form_data['boards'])
        form_data['boards'] = [b for b in form_data['boards'] if (b in media_conf['boards_with_thumb'] or b in media_conf['boards_with_image'])]
        b_f = len(form_data['boards'])
        if b_i > b_f:
            await flash('Some boards have media disabled, there may be fewer results than expected.')
        if not form_data['boards']:
            return [], 0

    if search_type == SearchType.idx:
        return await get_posts_and_total_hits_fts(form_data)
    return await get_posts_and_total_hits_sql(form_data)
