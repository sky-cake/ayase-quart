from urllib.parse import urlencode


def total_pages(total: int, hits_per_page: int) -> int:
    """
    Given
        - a total number of results (ex: 186)
        - a max number of results per page (ex: 10)
    determine how many pages there are (19)
    if there are no results
        0 pages
    if there are 1-10 results
        1 page
    if there are 11 results
        2 pages
    """
    # -(-total // q.hits_per_page) # https://stackoverflow.com/a/35125872
    if not total:
        return 0
    d, m = divmod(total, hits_per_page)
    if m > 0:
        return d + 1
    return d


def get_page_link(base_link: str, page: int, is_active: bool=False, text: str=None, section: str=None):
    text = page if text is None else text

    if is_active:
        is_active = ' class="is_active"'
        text = f'[{text}]'
    else:
        is_active = ''

    if section:
        section = f'#{section}'
    else:
        section = ''

    link = f'<a href="{base_link}&page={page}{section}">{text}</a>'
    wrapped = f'<li{is_active}>{link}</li>'
    return wrapped

def template_pagination_links(path: str, params: dict, total_pages: int, section: str=None):
    """
    Given
        total_pages:int
        and current_page:int
    return html of all the pages at the bottom of page
    is_active class for current page
    extra buttons:
        first, last, previous, next

    example page 2 of 4:
    <div class="paginate">
        <ul>
            <li><a href="fts?terms=hello+there&boards=g&page=1">First</a></li>
            <li><a href="fts?terms=hello+there&boards=g&page=1">Previous</a></li>
            <li><a href="fts?terms=hello+there&boards=g&page=1">1</a></li>
            <li class="is_active"><a href="fts?terms=hello+there&boards=g&page=2">2</a></li>
            <li><a href="fts?terms=hello+there&boards=g&page=3">3</a></li>
            <li><a href="fts?terms=hello+there&boards=g&page=4">4</a></li>
            <li><a href="fts?terms=hello+there&boards=g&page=3">Next</a></li>
            <li><a href="fts?terms=hello+there&boards=g&page=4">Last</a></li>
        </ul>
    </div>
    First Previous
        1 2 3 4
    Next Last
    """

    # no results or only 1 page of results
    if total_pages <= 1:
        return ''

    cur_page = params['page']

    # clamp
    if cur_page < 1:
        cur_page = 1
    if cur_page > total_pages:
        cur_page = total_pages

    params.pop('page', None)
    # params.pop('nums', None)
    # params.pop('thread_nums', None)

    params_t = []
    for k, v in params.items():
        if any(v == x for x in (None, '', False)):
            continue
        if type(v) is list:
            for e in v:
                params_t.append((k, e))
        else:
            params_t.append((k, v))
    enc_params = urlencode(params_t)
    base_link = f'{path}?{enc_params}'

    links = []

    if cur_page > 1: # not first page
        links.append(get_page_link(base_link, 1, text='First', section=section))
        links.append('<br>')
        links.append(get_page_link(base_link, cur_page - 1, text='Previous', section=section))
        links.append('<br>')

    page_range = 10 # 0, 1, 2, ..., (10 - cur), 11, 12, ..., 20
    lower = 1
    upper = total_pages
    if total_pages > page_range * 2:
        lower = max(1, cur_page - page_range)
        upper = min(total_pages, cur_page + page_range)

    for page_i in range(lower, upper + 1): # numbered links
        is_active = page_i == cur_page
        links.append(get_page_link(base_link, page_i, is_active=is_active, section=section))

    if cur_page < total_pages: # not last page
        links.append('<br>')
        links.append(get_page_link(base_link, cur_page + 1, text='Next', section=section))
        links.append('<br>')
        links.append(get_page_link(base_link, total_pages, text='Last', section=section))

    links = ''.join(links)
    return f'<div class="paginate"><ul>{links}</ul></div>'
