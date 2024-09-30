from functools import cache

from jinja2 import Template
from quart import render_template
from werkzeug.exceptions import NotFound

from configs import CONSTS


def validate_board_shortname(board_shortname: str) -> None:
    if not board_shortname in CONSTS.boards:
        raise NotFound(board_shortname, CONSTS.board_shortnames)

@cache
def get_title(board_shortname: str):
    title = f"/{board_shortname}/ - {CONSTS.boards[board_shortname]}"
    return title


async def render_controller(template: str | Template, **kwargs):
    """
    `template` should be a template file name (string), or a cached template (Template object).

    Using this function makes it easier to switch between debugging the UI, and maximizing performance.
    """

    if CONSTS.TESTING:
        return await render_template(template.name, **kwargs)

    if isinstance(template, Template):
        return template.render(**kwargs)
        # return await template.render_async(**kwargs) # not sure why quart's jinja2 env is setup like this...

    raise ValueError(CONSTS.TESTING, type(template), template)
