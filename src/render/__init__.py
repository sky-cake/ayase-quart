from jinja2 import Template
from quart import render_template

from configs import app_conf

TESTING = app_conf.get('testing', False)


async def render_controller(template: str | Template, **kwargs):
    """
    `template` should be a template file name (string), or a cached template (Template object).

    Using this function makes it easier to switch between debugging the UI, and maximizing performance.
    """

    if TESTING:
        return await render_template(template.name, **kwargs)

    if isinstance(template, Template):
        return template.render(**kwargs)
        # return await template.render_async(**kwargs) # not sure why quart's jinja2 env is setup like this...

    raise ValueError(TESTING, type(template), template)
