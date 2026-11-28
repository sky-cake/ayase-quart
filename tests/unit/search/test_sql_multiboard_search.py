import asyncio
import re
from copy import deepcopy

import pytest

from ayase_quart import asagi_converter
from ayase_quart.asagi_converter import search_posts
from ayase_quart.db import db_q


captured_queries: list[tuple[str, str, tuple]] = []


async def fake_query_tuple(sql, params=None, commit=False):
    captured_queries.append(('count', ' '.join(sql.split()), tuple(params) if params else ()))
    return [[3]]


async def fake_query_dict(sql, params=None, commit=False, dict_row=True):
    captured_queries.append(('select', ' '.join(sql.split()), tuple(params) if params else ()))
    return []


@pytest.fixture(autouse=True)
def capture_queries(monkeypatch):
    captured_queries.clear()
    monkeypatch.setattr(db_q, 'query_tuple', fake_query_tuple)
    monkeypatch.setattr(db_q, 'query_dict', fake_query_dict)
    monkeypatch.setattr(asagi_converter, 'validate_boards', lambda boards: None)
    yield
    captured_queries.clear()


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
        'thread_nums': None,
        'tl': None,
        'tlop': '=',
        'cl': None,
        'clop': '=',
        'op_title': None,
        'op_comment': None,
        'board_2_nums': None,
        'order_by': 'desc',
        'hits_per_page': 10,
        'page': 1,
    }


def run_search(form_data: dict, max_hits: int = 1_000):
    asyncio.run(search_posts(deepcopy(form_data), max_hits))


def get_queries(kind: str) -> list[tuple[str, tuple]]:
    return [(sql, params) for k, sql, params in captured_queries if k == kind]


def count_placeholders(sql: str) -> int:
    counter_ph = len(re.findall(r':\d+', sql))
    if counter_ph:
        return counter_ph
    return sql.count('?') + sql.count('%s')


def assert_placeholders_match_params(sql: str, params: tuple):
    n_ph = count_placeholders(sql)
    assert n_ph == len(params), f'placeholder/param mismatch ({n_ph} vs {len(params)}): {sql=}, {params=}'


def test_multiboard_op_title_placeholder_alignment():
    form_data = base_form_data(['a', 'b'])
    form_data['op_title'] = 'daily'

    run_search(form_data)

    count_queries = get_queries('count')
    select_queries = get_queries('select')

    assert len(count_queries) == 2
    assert len(select_queries) == 2

    for board in ('a', 'b'):
        count_sqls = [sql for sql, _ in count_queries if f'from `{board}`' in sql]
        assert len(count_sqls) == 1
        # exactly one facet subquery, referencing this board only
        assert count_sqls[0].count('op = 1 and') == 1
        assert count_sqls[0].count('thread_num in (select') == 1
        # no other board's table leaked into this query
        for other in ('a', 'b'):
            if other != board:
                assert f'`{other}`' not in count_sqls[0]

    for sql, params in count_queries:
        assert_placeholders_match_params(sql, params)

    for sql, params in select_queries:
        assert_placeholders_match_params(sql, params)


def test_multiboard_op_comment_placeholder_alignment():
    form_data = base_form_data(['a', 'b'])
    form_data['op_comment'] = 'hello there'

    run_search(form_data)

    count_queries = get_queries('count')
    assert len(count_queries) == 2

    for board in ('a', 'b'):
        sql, params = next((sql, params) for sql, params in count_queries if f'from `{board}`' in sql)
        assert sql.count('op = 1 and') == 1
        assert sql.count('thread_num in (select') == 1
        assert_placeholders_match_params(sql, params)
        # one facet param per board query
        assert len(params) == 1


def test_multiboard_op_title_and_op_comment():
    form_data = base_form_data(['a', 'b'])
    form_data['op_title'] = 'daily'
    form_data['op_comment'] = 'hello'

    run_search(form_data)

    count_queries = get_queries('count')
    assert len(count_queries) == 2

    for board in ('a', 'b'):
        sql, params = next((sql, params) for sql, params in count_queries if f'from `{board}`' in sql)
        # both facet conditions in a single subquery
        assert sql.count('thread_num in (select') == 1
        assert sql.count('op = 1 and') == 1
        assert 'title like' in sql
        assert 'comment like' in sql
        assert_placeholders_match_params(sql, params)
        assert len(params) == 2


def test_multiboard_op_title_with_base_filter():
    form_data = base_form_data(['a', 'b'])
    form_data['op_title'] = 'daily'
    form_data['comment'] = 'foo'

    run_search(form_data)

    count_queries = get_queries('count')
    assert len(count_queries) == 2

    for board in ('a', 'b'):
        sql, params = next((sql, params) for sql, params in count_queries if f'from `{board}`' in sql)
        assert sql.count('comment like') == 1
        assert sql.count('thread_num in (select') == 1
        assert_placeholders_match_params(sql, params)
        # 1 base comment param + 1 facet param
        assert len(params) == 2


def test_multiboard_tl_clause_not_duplicated():
    form_data = base_form_data(['a', 'b'])
    form_data['op_title'] = 'daily'
    form_data['tl'] = 10

    run_search(form_data)

    count_queries = get_queries('count')
    assert len(count_queries) == 2

    for sql, _ in count_queries:
        # the length filter must appear exactly once per query, not once per accumulated board
        assert len(re.findall(r'length\(title\) = 10', sql, re.IGNORECASE)) == 1


def test_multiboard_no_op_filter_unchanged():
    form_data = base_form_data(['a', 'b'])
    form_data['comment'] = 'foo'

    run_search(form_data)

    count_queries = get_queries('count')
    assert len(count_queries) == 2

    for sql, params in count_queries:
        assert 'thread_num in (select' not in sql
        assert_placeholders_match_params(sql, params)
        assert len(params) == 1
