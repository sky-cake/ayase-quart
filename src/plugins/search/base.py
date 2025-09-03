from abc import ABC, abstractmethod
from forms import SearchForm

class SearchPlugin(ABC):
    @abstractmethod
    async def get_boards_2_nums(self, form: SearchForm) -> dict[str, set[int]]:
        """
        Return a dict of {board1: set(num1, num2), ...}
        """
        pass
