from abc import ABC, abstractmethod
from typing import Iterable


class BasePoolManager(ABC):
    @abstractmethod
    async def create_pool(self, identifier='id1', **kwargs):
        """Create a pool."""
        pass

    @abstractmethod
    async def get_pool(self, identifier='id1', store=True, **kwargs):
        """Get a pool."""
        pass

    @abstractmethod
    async def close_pool(self, identifier='id1'):
        """Close a specific pool."""
        pass

    @abstractmethod
    async def close_all_pools(self):
        """Close all pools."""
        pass


class BaseQueryRunner(ABC):
    @abstractmethod
    async def run_query(self, query: str, params=None, commit=False, identifier='id1', dict_row=True):
        """Executes a query. Allows writing to database."""
        pass

    @abstractmethod
    async def run_query_fast(self, query: str, params=None, identifier='id1'):
        """Executes a fast query mainly by avoiding the creation of dict objects."""
        pass


class BasePlaceHolderGen():
    __slots__ = ()

    def size(self, items: Iterable):
        return ','.join(self() for _ in range(len(items)))

    def qty(self, qty: int):
        return ','.join(self() for _ in range(qty))