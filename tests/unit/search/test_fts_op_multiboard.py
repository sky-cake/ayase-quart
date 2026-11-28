import asyncio
from collections import defaultdict

import pytest

from ayase_quart.configs import index_search_conf
from ayase_quart import search as search_mod
from ayase_quart.search import _get_posts_and_total_hits_fts
from ayase_quart.search.post_metadata import board_2_int
from ayase_quart.search.providers.lnx import LnxSearch
from ayase_quart.search.query import IndexSearchQuery


class FakeSearchProvider:
    def __init__(self, facet_pages: list[dict], facet_total: int, search_total: int = 0):
        self.facet_pages = facet_pages
        self.facet_total = facet_total
        self.search_total = search_total
        self.facet_queries: list[IndexSearchQuery] = []
        self.search_queries: list[IndexSearchQuery] = []

    async def search_posts_get_thread_nums(self, q: IndexSearchQuery):
        self.facet_queries.append(q)
        page = q.page or 1
        if page <= len(self.facet_pages):
            return self.facet_pages[page - 1], self.facet_total
        return {}, self.facet_total

    async def search_posts(self, q: IndexSearchQuery):
        self.search_queries.append(q)
        return [], self.search_total


@pytest.fixture
def fake_provider(monkeypatch):
    provider = FakeSearchProvider(facet_pages=[], facet_total=0)
    # search/__init__ binds get_index_search_provider at import time, so patch there
    monkeypatch.setattr(search_mod, 'get_index_search_provider', lambda: provider)
    return provider


def base_form_data(boards: list[str]) -> dict:
    return {
        'boards': boards,
        'title': None,
        'comment': None,
        'media_filename': None,
        'media_hash': None,
        'date_before': None,
        'date_after': None,
        'has_no_file': None,
        'has_file': None,
        'is_op': None,
        'is_not_op': None,
        'is_deleted': None,
        'is_not_deleted': None,
        'is_sticky': None,
        'is_not_sticky': None,
        'width': None,
        'wop': '=',
        'height': None,
        'hop': '=',
        'capcode': 'any',
        'num': None,
        'nums': None,
        'thread_nums': None,
        'board_2_nums': None,
        'tripcode': None,
        'tl': None,
        'tlop': '=',
        'cl': None,
        'clop': '=',
        'op_title': None,
        'op_comment': None,
        'order_by': 'desc',
        'hits_per_page': 50,
        'page': 1,
    }


def make_facet_pages(boards_2_nums: dict[str, list[int]]) -> list[dict]:
    flat = [(board, num) for board, nums in boards_2_nums.items() for num in nums]
    chunk_size = index_search_conf.max_hits
    pages = []
    for i in range(0, len(flat), chunk_size):
        page: dict[str, list[int]] = defaultdict(list)
        for board, num in flat[i:i + chunk_size]:
            page[board].append(num)
        pages.append(dict(page))
    return pages


def test_multiboard_op_search_single_final_query(fake_provider):
    fake_provider.facet_pages = make_facet_pages({'a': [100, 101], 'b': [200]})
    fake_provider.facet_total = 3
    fake_provider.search_total = 42

    form_data = base_form_data(['a', 'b'])
    form_data['op_title'] = 'daily'

    posts, total_hits = asyncio.run(_get_posts_and_total_hits_fts(form_data))

    assert (posts, total_hits) == ([], 42)
    assert len(fake_provider.facet_queries) == 1
    assert len(fake_provider.search_queries) == 1

    facet_q = fake_provider.facet_queries[0]
    assert facet_q.op is True
    assert facet_q.title == 'daily'
    assert facet_q.comment is None
    assert facet_q.boards == [board_2_int('a'), board_2_int('b')]

    final_q = fake_provider.search_queries[0]
    # the final query must not be OP-restricted, replies are expected too
    assert final_q.op is None
    # global pagination straight from the form, not per board
    assert final_q.hits_per_page == 50
    assert final_q.page == 1
    # per-board thread restriction
    assert final_q.board_2_thread_nums == {
        board_2_int('a'): {100, 101},
        board_2_int('b'): {200},
    }
    # the unsafe cross-board thread_nums path must not be used
    assert final_q.thread_nums is None


def test_facet_collection_capped_at_max_hits(fake_provider):
    max_hits = index_search_conf.max_hits
    nums = list(range(max_hits * 2 + 7))
    fake_provider.facet_pages = make_facet_pages({'a': nums})
    fake_provider.facet_total = len(nums)

    form_data = base_form_data(['a'])
    form_data['op_comment'] = 'foo'

    asyncio.run(_get_posts_and_total_hits_fts(form_data))

    # the facet fetch is capped at max_hits: a single request collects at most max_hits thread nums
    assert len(fake_provider.facet_queries) == 1
    assert fake_provider.facet_queries[0].page == 1

    final_q = fake_provider.search_queries[0]
    assert final_q.board_2_thread_nums == {board_2_int('a'): set(nums[:max_hits])}


def test_no_op_threads_returns_empty(fake_provider):
    fake_provider.facet_pages = []
    fake_provider.facet_total = 0

    form_data = base_form_data(['a', 'b'])
    form_data['op_title'] = 'daily'

    posts, total_hits = asyncio.run(_get_posts_and_total_hits_fts(form_data))

    assert (posts, total_hits) == ([], 0)
    assert len(fake_provider.facet_queries) == 1
    assert fake_provider.search_queries == []


def test_plugin_board_2_nums_stays_separate_clause(fake_provider):
    fake_provider.facet_pages = make_facet_pages({'a': [100, 101]})
    fake_provider.facet_total = 2

    form_data = base_form_data(['a', 'b'])
    form_data['op_title'] = 'daily'
    # plugin results restrict specific post nums
    form_data['board_2_nums'] = {'a': {123, 456}}

    asyncio.run(_get_posts_and_total_hits_fts(form_data))

    final_q = fake_provider.search_queries[0]
    # thread restriction on thread_num...
    assert final_q.board_2_thread_nums == {board_2_int('a'): {100, 101}}
    # ...and post restriction on num, as separate ANDed clauses
    assert final_q.board_2_nums == {board_2_int('a'): {123, 456}}


def test_lnx_query_builder_board_2_thread_nums():
    board_int = board_2_int('a')
    q = IndexSearchQuery(
        boards=[board_int],
        board_2_thread_nums={board_int: [1, 2]},
    )
    built = LnxSearch._query_builder(None, q)

    assert {
        'occur': 'must',
        'normal': {
            'ctx': f'(board:{board_int}) AND (thread_num:1 OR thread_num:2)',
        },
    } in built


def test_lnx_query_builder_multiboard_thread_pairs():
    a_int, b_int = board_2_int('a'), board_2_int('b')
    q = IndexSearchQuery(
        boards=[a_int, b_int],
        board_2_thread_nums={a_int: [1], b_int: [2]},
    )
    built = LnxSearch._query_builder(None, q)

    ctxs = [clause['normal']['ctx'] for clause in built]
    assert f'(board:{a_int}) AND (thread_num:1) OR (board:{b_int}) AND (thread_num:2)' in ctxs
