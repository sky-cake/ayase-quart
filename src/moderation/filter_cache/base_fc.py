import re
from abc import ABC, abstractmethod

from asagi_converter import (
    get_deleted_numops_by_board,
    get_numops_by_board_and_regex
)
from boards import board_shortnames

class BaseFilterCache(ABC):
    def __init__(self, mod_conf: dict):
        self.enabled = mod_conf['enabled']
        self.remove_replies_to_hidden_op = mod_conf['remove_replies_to_hidden_op']
        self.regex_filter = mod_conf['regex_filter']
        self.hide_upstream_deleted_posts = mod_conf['hide_upstream_deleted_posts']

        super().__init__()

    async def init(self):
        if not self.enabled:
            return

        await self._create_cache()

    async def get_deleted_numops_per_board_iter(self):
        """Returns a tuple[str, tuple[int, int]]

        `(board, [(num, op), ...])`
        """
        if not (self.hide_upstream_deleted_posts and board_shortnames):
            return
        for board in board_shortnames:
            numops = await get_deleted_numops_by_board(board)
            yield board, numops

    async def get_numops_by_board_and_regex_iter(self):
        """Returns a tuple[str, tuple[int, int]]

        `(board, [(num, op), ...])`
        """
        if not (self.regex_filter and board_shortnames):
            return
        for board in board_shortnames:
            numops = await get_numops_by_board_and_regex(board, self.regex_filter)
            yield board, numops

    @abstractmethod
    async def _create_cache(self) -> None:
        """Create the db schema, filter in redis, whatever"""
        raise NotImplementedError()

    @abstractmethod
    async def _is_cache_populated(self) -> bool:
        """Check if the population routine must be ran"""
        raise NotImplementedError()

    @abstractmethod
    async def _populate_cache(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _teardown(self) -> None:
        """Remove all inserts"""
        raise NotImplementedError()

    @abstractmethod
    async def is_post_removed(self, board: str, num: int) -> bool:
        """Is the post removed?"""
        raise NotImplementedError()

    @abstractmethod
    async def get_op_thread_removed_count(self, board: str) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def insert_post(self, board: str, num: int, op: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def delete_post(self, board: str, num: int, op: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_board_num_pairs(self, posts: list) -> set[tuple[str, int]]:
        """`set[('g', 12345), ('x', 6789), ...]`"""
        raise NotImplementedError()

    def should_filter(self, board_num_pairs: set, post: dict) -> bool:
        return (
            (self.remove_replies_to_hidden_op and (post['board_shortname'], post['thread_num']) in board_num_pairs)
            or
            ((post['board_shortname'], post['num']) in board_num_pairs)
            or
            (self.hide_upstream_deleted_posts and post['deleted'])
            or
            (self.regex_filter and post['comment'] and re.search(self.regex_filter, post['comment'], re.IGNORECASE))
        )

    async def filter_reported_posts(self, posts: list[dict], is_authority: bool=False) -> list:
        if not self.enabled:
            return posts

        if not posts:
            return posts

        board_num_pairs = await self.get_board_num_pairs(posts)

        note = 'Only visible to AQ staff.'

        if is_authority:
            return [
                post
                if not self.should_filter(board_num_pairs, post)
                else post | dict(deleted=note)
                for post in posts
            ]
        return [
            post for post in posts
            if not self.should_filter(board_num_pairs, post)
        ]
