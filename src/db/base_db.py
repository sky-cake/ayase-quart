from abc import ABC, abstractmethod
from typing import Iterable

from enums import DbPool


class BasePoolManager(ABC):
    @abstractmethod
    async def create_pool(self, p_id=DbPool.main, **kwargs):
        """Create a pool."""
        pass

    @abstractmethod
    async def get_pool(self, p_id=DbPool.main, store=True, **kwargs):
        """Get a pool."""
        pass

    @abstractmethod
    async def close_pool(self, p_id=DbPool.main):
        """Close a specific pool."""
        pass

    @abstractmethod
    async def close_all_pools(self):
        """Close all pools."""
        pass


class BaseQueryRunner(ABC):
    @abstractmethod
    async def run_query(self, query: str, params=None, commit=False, p_id=DbPool.main, dict_row=True):
        """Executes a query. Allows writing to database."""
        pass

    @abstractmethod
    async def run_query_fast(self, query: str, params=None, p_id=DbPool.main):
        """Executes a fast query mainly by avoiding the creation of dict objects."""
        pass


class BasePlaceHolderGen():
    __slots__ = ()

    def size(self, items: Iterable):
        return ','.join(self() for _ in range(len(items)))

    def qty(self, qty: int):
        return ','.join(self() for _ in range(qty))