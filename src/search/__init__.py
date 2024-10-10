from configs import search_conf

SEARCH_ENABLED: bool = search_conf.get('enabled', False)
HIGHLIGHT_ENABLED: bool = search_conf.get('highlight', False)
DEFAULT_RESULTS_LIMIT: int = search_conf.get('default_result_limit', 100)
MAX_RESULTS_LIMIT: int = search_conf.get('max_result_limit', 10000)