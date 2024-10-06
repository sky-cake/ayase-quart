from configs2 import search_conf

SEARCH_ENABLED = search_conf.get('enabled', False)
HIGHLIGHT_ENABLED = search_conf.get('highlight', False)
DEFAULT_RESULTS_LIMIT = search_conf.get('default_result_limit', 100)
MAX_RESULTS_LIMIT = search_conf.get('max_result_limit', 10000)