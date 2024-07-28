def total_pages(total: int, per_page: int) -> int:
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
    # -(-total // q.result_limit) # https://stackoverflow.com/a/35125872
    if not total:
        return 0
    d, m = divmod(total, per_page)
    if m > 0:
        return d + 1
    return d


def template_pagination_links(total_pages: int, cur_page: int, params: dict):
    """
    TODO: template paging links

    Given
        total_pages:int
        and current_page:int
    return html of all the pages at the bottom of page
    extra buttons:
        first, last, previous, next
    """
    pass
