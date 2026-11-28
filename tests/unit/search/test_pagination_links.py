from urllib.parse import parse_qs

from ayase_quart.search.pagination import get_total_pages, template_pagination_links


def get_query_params(link: str) -> dict:
    href = link.split('href="')[1].split('"')[0]
    return parse_qs(href.split('?')[1])


def test_multiboard_boards_csv_in_single_param():
    params = {
        'boards': ['g', 'b'],
        'comment': 'foo',
        'page': 2,
        'hits_per_page': 50,
    }
    links = template_pagination_links('/fts', params, total_pages=3)

    assert links  # 3 pages -> links rendered
    parsed = get_query_params(links)

    # one boards param with csv value, not one param per board
    # (routes parse args with `to_dict(flat=True)`, repeated keys lose all but the first value)
    assert len(parsed['boards']) == 1
    assert parsed['boards'][0].split(',') == ['g', 'b']


def test_single_board_unchanged():
    params = {
        'boards': ['g'],
        'page': 2,
    }
    links = template_pagination_links('/fts', params, total_pages=2)
    parsed = get_query_params(links)

    assert parsed['boards'] == ['g']


def test_scalar_params_unchanged():
    params = {
        'boards': 'g',
        'comment': 'foo bar',
        'page': 1,
    }
    links = template_pagination_links('/fts', params, total_pages=2)
    parsed = get_query_params(links)

    assert parsed['boards'] == ['g']
    assert parsed['comment'] == ['foo bar']


def test_falsy_params_dropped():
    params = {
        'boards': 'g',
        'comment': None,
        'title': '',
        'has_file': False,
        'page': 1,
    }
    links = template_pagination_links('/fts', params, total_pages=2)
    parsed = get_query_params(links)

    assert 'comment' not in parsed
    assert 'title' not in parsed
    assert 'has_file' not in parsed


def test_empty_list_dropped():
    params = {
        'boards': [],
        'comment': 'foo',
        'page': 1,
    }
    links = template_pagination_links('/fts', params, total_pages=2)
    parsed = get_query_params(links)

    assert 'boards' not in parsed
    assert parsed['comment'] == ['foo']


def test_get_total_pages():
    assert get_total_pages(0, 50) == 0
    assert get_total_pages(1, 50) == 1
    assert get_total_pages(50, 50) == 1
    assert get_total_pages(51, 50) == 2
    assert get_total_pages(100, 50) == 2
    assert get_total_pages(101, 50) == 3
