from ..asagi_converter import search_posts
from ..configs import index_search_conf, vanilla_search_conf
from .post_metadata import board_2_int
from .providers import get_index_search_provider
from .query import IndexSearchQuery, get_index_search_query

# should probably make /fts and /sql StrEnums
# definitely not url_for, otherwise circular import headaches
BEST_SEARCH_ENDPOINT: str = '/fts' if index_search_conf.enabled else ('/sql' if vanilla_search_conf.enabled else '')

async def _get_posts_and_total_hits_fts(form_data: dict) -> tuple[list[dict], int]:
    if not isinstance(form_data['boards'], list):
        raise ValueError(form_data['boards'])

    index_searcher = get_index_search_provider()
    board_ints = [board_2_int(board) for board in form_data['boards']]

    if form_data['op_title'] or form_data['op_comment']:
        # two-step search,
        # 1. find thread_nums per board for op_title, op_comment queries
        # 2. search for those thread_nums while keeping board:thread_num integrity
        facet_q = IndexSearchQuery(
            op=True,
            comment=form_data['op_comment'] if form_data['op_comment'] else None,
            title=form_data['op_title'] if form_data['op_title'] else None,
            boards=board_ints,
            hits_per_page=index_search_conf.max_hits,
        )

        # note: capped at index_search_conf.max_hits, not index_search_conf.hits_per_page
        # this functions like our sql search
        page_board_2_nums, total_hits = await index_searcher.search_posts_get_thread_nums(facet_q)

        if not total_hits or not page_board_2_nums:
            return [], 0

        boards_2_threadnums: dict[int, set[int]] = {board_2_int(board): set(nums) for board, nums in page_board_2_nums.items()}

        # search-plugins use board_2_nums
        # some deduplication could be done here, but it likely doesn't make a difference
        query = get_index_search_query(form_data)
        query.board_2_thread_nums = boards_2_threadnums
        return await index_searcher.search_posts(query)

    query = get_index_search_query(form_data, board_ints=board_ints)
    return await index_searcher.search_posts(query)


async def get_posts_and_total_hits_fts(form_data: dict):
    return await _get_posts_and_total_hits_fts(form_data)


async def get_posts_and_total_hits_sql(form_data: dict):
    return await search_posts(form_data, vanilla_search_conf.max_hits)
