import quart_flask_patch  # noqa

import asyncio
import os
import traceback

from flask_bootstrap import Bootstrap5
from quart import Quart
from werkzeug.exceptions import HTTPException

from blueprints import blueprints
from configs import QuartConfig, app_conf, mod_conf
from db import db_q
from moderation import init_moderation
from moderation.filter_cache import fc
from render import render_controller
from templates import render_constants, template_message
from quart_schema import RequestSchemaValidationError


def print_exception(e: Exception):
    print(''.join(traceback.format_exception(type(e), e, e.__traceback__)))


async def api_validation_exception(e: RequestSchemaValidationError):
    return {'error': str(e.description)}, 400


async def http_exception(e: HTTPException):
    render = await render_controller(template_message, message=e, tab_title=f'Error', title='Uh-oh...')
    return render, e.code


async def app_exception(e: Exception):
    print_exception(e) # should log these errors

    message = 'We\'re sorry, our server ran into an issue.'
    if app_conf.get('testing'):
        message = e

    render = await render_controller(template_message, message=message, tab_title=f'Error', title='Uh-oh...')
    return render


async def create_app():
    file_dir = os.path.dirname(__file__)
    os.chdir(file_dir)

    app = Quart(__name__)

    app.config.from_object(QuartConfig)
    app.config['MATH_CAPTCHA_FONT'] = os.path.join(file_dir, 'fonts/tly.ttf')

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

    if mod_conf['moderation']:
        from moderation.auth import auth_api, auth_web
        from quart_schema import QuartSchema
        auth_api.init_app(app)
        auth_web.init_app(app)
        QuartSchema(app)

    app.register_error_handler(HTTPException, http_exception)
    app.register_error_handler(Exception, app_exception)
    app.register_error_handler(RequestSchemaValidationError, api_validation_exception)

    return app


app = asyncio.run(create_app())

if not app_conf.get('testing', False):
    print('Quart app created. Now, since you\'re not in dev mode, point hypercorn to this asgi app with something like,')
    print('    hypercorn --config hypercorn.toml ./src/main:app')
    print('Hypercorn config docs at: https://hypercorn.readthedocs.io/en/latest/how_to_guides/configuring.html')
    print('If you want to exit, use ctrl-c and/or ctrl-z.')

elif __name__ == '__main__':
    app.run(
        '127.0.0.1',
        port=app_conf.get('port', 9001),
        debug=True,
        certfile=app_conf.get('ssl_cert'),
        keyfile=app_conf.get('ssl_key'),
        use_reloader=app_conf.get('autoreload', True),
    )
else:
    print('Nothing to do.')

