import quart_flask_patch  # isort: skip  # noqa: F401

import asyncio
import os

from flask_bootstrap import Bootstrap5
from quart import Quart, request
from quart_auth import QuartAuth, current_user
from werkzeug.exceptions import HTTPException

from blueprints import blueprints
from configs import QuartConfig, app_conf, mod_conf
from db import db_q
from moderation import init_moderation
from moderation.filter_cache import fc
from moderation.user import User
from render import render_controller
from templates import render_constants, template_message
from utils import Perf

# from security.limiter import limiter


async def http_exception(e: HTTPException):
    p = Perf('http error')
    render = await render_controller(template_message, message=e, tab_title=f'Error', title='Uh-oh...')
    p.check('render')
    print(p)
    return render


async def app_exception(e: Exception):
    p = Perf('app error')

    message = 'We\'re sorry, our server ran into an issue.'
    if app.testing:
        message = e

    render = await render_controller(template_message, message=message, tab_title=f'Error', title='Uh-oh...')
    p.check('render')
    print(p)
    return render


async def load_user():
    # this gets hammered by every request...
    if request.endpoint == 'bp_media.serve':
        return
    await current_user.load_user_data()


async def create_app():
    file_dir = os.path.dirname(__file__)
    os.chdir(file_dir)

    app = Quart(__name__)

    app.config.from_object(QuartConfig)

    # limiter.init_app(app)

    app.config['MATH_CAPTCHA_FONT'] = os.path.join(file_dir, "fonts/tly.ttf")

    Bootstrap5(app)
    app.jinja_env.auto_reload = False
    app.jinja_env.globals.update(render_constants)

    for bp in blueprints:
        app.register_blueprint(bp)

    if mod_conf['moderation']:
        await init_moderation()
        await fc.init()

    # https://quart.palletsprojects.com/en/latest/how_to_guides/startup_shutdown.html#startup-and-shutdown
    app.before_serving(db_q.prime_db_pool)
    app.after_serving(db_q.close_db_pool)

    app.before_request(load_user)
    # app.before_websocket(load_user) # we currently do not use websockets

    auth_manager = QuartAuth()
    auth_manager.user_class = User
    auth_manager.init_app(app)

    app.register_error_handler(HTTPException, http_exception)
    app.register_error_handler(Exception, app_exception)

    return app


app = asyncio.run(create_app())

if __name__ == '__main__' and app_conf.get('testing', False):
    app.run(
        '127.0.0.1',
        port=app_conf.get('port', 9001),
        debug=True,
        certfile=app_conf.get('ssl_cert'),
        keyfile=app_conf.get('ssl_key'),
        use_reloader=app_conf.get('autoreload', True),
    )
