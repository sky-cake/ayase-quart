from configs import search_conf

SEARCH_ENABLED: bool = search_conf.get('enabled', False)
HIGHLIGHT_ENABLED: bool = search_conf.get('highlight', False)
HITS_PER_PAGE: int = search_conf.get('hits_per_page', 100)
MAX_HITS: int = search_conf.get('max_hits', 10_000)