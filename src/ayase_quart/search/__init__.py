from ..asagi_converter import search_posts
from ..configs import index_search_conf, vanilla_search_conf
from .post_metadata import board_2_int
from .providers import get_index_search_provider
from .query import IndexSearchQuery, get_index_search_query


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
        # TODO: introduce form_data['boards_2_threadnums'] = boards_2_threadnums
        # this results in 1 query rather than len(boards) queries
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
