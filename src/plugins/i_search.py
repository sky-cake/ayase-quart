import importlib
import pkgutil
from abc import ABC, abstractmethod

from forms import SearchForm
from jinja2 import Template
from wtforms import Field


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


async def intersect_search_plugin_results(search_plugins: dict[str, SearchPlugin], form: SearchForm) -> dict[str, set[int]]:
    """
    Returns the intersection of each plugins' boards and nums.
    I.e. if plugin #1 returns 0 results, and plugin #2 returns 100 results, we return 0 results.
    """
    boards_2_nums: dict[str, set[int]] = dict()

    if not search_plugins:
        return boards_2_nums

    first_loop = True
    for plugin_name, plugin in search_plugins.items():
        _boards_2_nums: dict[str, set[int]] = await plugin.get_boards_2_nums(form)

        if first_loop:
            if _boards_2_nums:
                boards_2_nums = _boards_2_nums.copy()
            else:
                # no results on first loop -> the intersection of any other results will be nothing
                return dict()

            first_loop = False
            continue

        if _boards_2_nums:
            for board, nums in _boards_2_nums.items():
                assert isinstance(nums, set)
                if board not in boards_2_nums:
                    continue
                boards_2_nums[board].intersection_update(nums)
                if not boards_2_nums[board]:
                    boards_2_nums.pop(board)

    return boards_2_nums


def load_search_plugins() -> dict[str, SearchPlugin]:
    """Returns {<plugin module name>: <SearchPlugin>}"""
    plugins: dict[str, SearchPlugin] = {}
    package_module = importlib.import_module('plugins.search')

    for _, module_name, is_pkg in pkgutil.iter_modules(package_module.__path__, package_module.__name__ + '.'):
        module = importlib.import_module(module_name)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, SearchPlugin) and attr is not SearchPlugin:
                print(f'Loading search plugin: {module_name}')
                plugins[module_name] = attr()
    return plugins


search_plugins = load_search_plugins()
