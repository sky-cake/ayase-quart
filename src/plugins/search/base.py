from abc import ABC, abstractmethod
from forms import SearchForm
from wtforms import Field
from jinja2 import Template


class SearchPlugin(ABC):
    fields: list[Field] = []

    # any html in this string WILL be rendered
    template: Template

    @abstractmethod
    async def get_boards_2_nums(self, form: SearchForm) -> dict[str, set[int]]:
        """
        Return a dict of {board1: set(num1, num2), ...}
        """
        pass
