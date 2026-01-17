from .base_fc import BaseFilterCache

empty_set = set()
class FilterCacheNull(BaseFilterCache):
    def __init__(self, mod_conf: dict):
        super().__init__(mod_conf)

    async def _create_cache(self) -> None: pass
    async def _is_cache_populated(self) -> bool: return True
    async def _populate_cache(self) -> None: pass
    async def _teardown(self) -> None: pass
    async def is_post_removed(self, board: str, num: int) -> bool: return False
    async def get_op_thread_removed_count(self, board: str) -> int: return 0
    async def get_board_num_pairs(self, posts: list) -> set[tuple[str, int]]: return empty_set
    async def insert_post(self, board: str, num: int, op: int) -> None: pass
    async def delete_post(self, board: str, num: int, op: int) -> None: pass
