import quart_flask_patch  # noqa
import os
import traceback

from quart import Quart, jsonify, current_app
from werkzeug.exceptions import HTTPException
from quart_schema import RequestSchemaValidationError
from hypercorn.middleware import ProxyFixMiddleware
from quart_rate_limiter import RateLimiter

from blueprints import blueprints # importing timm and torch down the import hole makes this slow
from configs import QuartConfig, app_conf, mod_conf, tag_conf, archiveposting_conf, traffic_log_conf
from db import db_q
from db.redis import close_redis
from moderation import init_moderation
from tagging.db import init_tagging
from moderation import fc
from render import render_controller
from templates import render_constants, template_error_message
from archiveposting import init_archiveposting


async def print_exception(e: Exception):
    msg = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
    app.logger.error(msg)
    print(msg)


async def api_validation_exception(e: RequestSchemaValidationError):
    return jsonify({'error': str(e.description)}), 400


async def http_exception(e: HTTPException):
    render = await render_controller(template_error_message, message=e, tab_title='Error', title='Uh-oh...')
    return render, e.code


async def app_exception(e: Exception):
    current_app.logger.error(''.join(traceback.format_exception(type(e), e, e.__traceback__)))

    message = 'We\'re sorry, our server ran into an issue.'
    if app_conf.get('testing'):
        message = e

    render = await render_controller(template_error_message, message=message, tab_title='Error', title='Uh-oh...')
    return render, 500


async def close_dbs():
    wait_close_db = db_q.close_db_pool()
    close_redis()
    await wait_close_db


def create_app():
    file_dir = os.path.dirname(__file__)
    os.chdir(file_dir)

    app = Quart(__name__)

    app.config.from_object(QuartConfig)
    app.config['MATH_CAPTCHA_FONT'] = os.path.join(file_dir, 'fonts/tly.ttf')

    RateLimiter(app, enabled=app_conf['rate_limiter'])

    app.jinja_env.auto_reload = app_conf['autoreload']
    app.jinja_env.globals.update(render_constants)

    for bp in blueprints:
        app.register_blueprint(bp)

    if mod_conf['enabled']:
        app.before_serving(init_moderation)
        app.before_serving(fc.init)

    if tag_conf['enabled']:
        app.before_serving(init_tagging)

    if archiveposting_conf['enabled']:
        app.before_serving(init_archiveposting)

    # https://quart.palletsprojects.com/en/latest/how_to_guides/startup_shutdown.html#startup-and-shutdown
    app.before_serving(db_q.prime_db_pool)
    app.after_serving(close_dbs)

    if mod_conf['enabled']:
        from moderation.auth import auth_api, auth_web
        from quart_schema import QuartSchema
        auth_api.init_app(app)
        auth_web.init_app(app)
        QuartSchema(app)

    if not app_conf.get('testing'):
        app.register_error_handler(HTTPException, http_exception)
        app.register_error_handler(Exception, app_exception)
        app.register_error_handler(RequestSchemaValidationError, api_validation_exception)

    if app_conf.get('proxy_trusted_hops', 0):
        app = ProxyFixMiddleware(app, mode="legacy", trusted_hops=1).app

    return app


app = create_app()


if not app_conf.get('testing', False):
    print('Quart app initialized in production mode.')
    print('If you want to run this in production, you should stop this process with CTRL-C')
    print('and point hypercorn to this asgi app with one of the following:')
    print('    1. /aq/venv/bin/hypercorn --config file:/aq/src/hypercorn_conf.py /aq/src/main:app')
    print('    2. hypercorn --config hypercorn.toml /aq/src/main:app')
    print('    3. hypercorn --bind 0.0.0.0:9003 --workers 3 /aq/src/main:app')
    print('Note: these are examples only. You ought to study the configs you use.')
    print('Hypercorn configs are documented at https://hypercorn.readthedocs.io/en/latest/how_to_guides/configuring.html')

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
    print('Quart app initialized in production mode. - AQ')
