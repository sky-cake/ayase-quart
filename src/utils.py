from configs import CONSTS
from quart import render_template
from jinja2 import Template
from werkzeug.exceptions import NotFound

def validate_board_shortname(board_shortname: str) -> None:
    if not board_shortname in CONSTS.board_shortnames:
        raise NotFound(board_shortname, CONSTS.board_shortnames)

def validate_threads(threads):
    if len(threads) < 1:
        raise NotFound(threads)
    
def validate_post(post):
    if len(post) < 1:
        raise NotFound(post)
    
def get_title(board_shortname):
    title = f"/{board_shortname}/ - {CONSTS.board_shortname_to_name[board_shortname]}"
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
    
    raise ValueError(CONSTS.TESTING, type(template), template)
