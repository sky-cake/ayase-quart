from abc import ABC, abstractmethod
from typing import Iterable


class BasePoolManager(ABC):
    @abstractmethod
    async def get_pool(self, **kwargs):
        """Get the pool, create it if it does not exist yet."""
        pass

    @abstractmethod
    async def close_pool(self):
        """Close the pool if it exists."""
        pass


class BaseQueryRunner(ABC):
    @abstractmethod
    async def run_query(self, query: str, params=None, commit=False, dict_row=True):
        """Executes a query. Allows writing to database."""
        pass

    @abstractmethod
    async def run_query_fast(self, query: str, params=None):
        """Executes a fast query mainly by avoiding the creation of dict objects."""
        pass

    @abstractmethod
    async def run_script(self, query: str):
        """Executes multiple sql statements, no params available"""
        pass


class BasePlaceHolderGen():
    __slots__ = ()

    def __init__(self, **kwargs):
        # swallow kwargs so signatures match
        pass

    def size(self, items: Iterable):
        return ','.join(self() for _ in range(len(items)))

    def qty(self, qty: int):
        return ','.join(self() for _ in range(qty))
