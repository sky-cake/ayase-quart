import importlib
import pkgutil
from abc import ABC, abstractmethod

from forms import SearchForm
from jinja2 import Template
from wtforms import Field
from utils import Perf


class SearchPluginResult:
    def __init__(self):
        self.board_2_nums: dict[str, set[int]] = dict()
        
        # html to show the user after plugin searches
        self.flash_msg: str = ''
        
        # helps determine if we should do a native search
        self.performed_search = False

    def add_flash_msg(self, msg: str):
        if msg:
            if self.flash_msg:
                self.flash_msg += '<br>'
            self.flash_msg += msg


class SearchPlugin(ABC):
    fields: list[Field] = []

    # any html in this string WILL be rendered
    template: Template

    @abstractmethod
    async def get_search_plugin_result(self, form: SearchForm, p: Perf) -> SearchPluginResult:
        pass


async def intersect_search_plugin_results(search_plugins: dict[str, SearchPlugin], form: SearchForm, p: Perf) -> SearchPluginResult:
    """
    Returns the intersection of each plugins' boards and nums.
    I.e. if plugin #1 returns 0 results, and plugin #2 returns 100 results, we return 0 results.
    """
    result = SearchPluginResult()

    if not search_plugins:
        return result

    first_loop = True
    for plugin_name, plugin in search_plugins.items():
        p.check(f'starting "{plugin_name}"')
        _result: SearchPluginResult = await plugin.get_search_plugin_result(form, p)
        p.check(f'done "{plugin_name}"')

        # once True, stay True
        result.performed_search = _result.performed_search or result.performed_search

        if not _result.board_2_nums:
            # the intersection of any other results will be nothing
            # keep the latest result's flash msg
            return _result

        result.add_flash_msg(_result.flash_msg)

        if first_loop:
            result.board_2_nums = {b: s.copy() for b, s in _result.board_2_nums.items()}
            first_loop = False
            continue

        for board, nums in _result.board_2_nums.items():
            if not isinstance(nums, set):
                raise TypeError(type(nums))

            if board not in result.board_2_nums:
                # no matching boards, no intersection
                continue

            result.board_2_nums[board].intersection_update(nums)
            if not result.board_2_nums[board]:
                result.board_2_nums.pop(board)

    return result


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
