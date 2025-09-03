from plugins.search.base import SearchPlugin
from forms import SearchForm


class SearchPluginExample(SearchPlugin):
    async def get_boards_2_nums(self, form: SearchForm) -> dict[str, set[int]]:
        return dict()
