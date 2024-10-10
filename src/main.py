import quart_flask_patch  # isort: skip

import asyncio
import os

from flask_bootstrap import Bootstrap5
from quart import Quart

from blueprint_admin import blueprint_admin
from blueprint_api import blueprint_api
from blueprint_app import blueprint_app
from blueprint_auth import blueprint_auth
from blueprint_moderation import blueprint_moderation
from blueprint_search import blueprint_search
from configs import QuartConfig, app_conf
from db import close_db_pool, prime_db_pool
from moderation.api import init_moderation_db
# from limiter import limiter
from templates import render_constants

if app_conf.get('testing', False):
    import tracemalloc
    tracemalloc.start()


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

    app.register_blueprint(blueprint_api)
    app.register_blueprint(blueprint_app)
    app.register_blueprint(blueprint_admin)
    app.register_blueprint(blueprint_auth)
    app.register_blueprint(blueprint_search)
    app.register_blueprint(blueprint_moderation)

    await init_moderation_db()

    # https://quart.palletsprojects.com/en/latest/how_to_guides/startup_shutdown.html#startup-and-shutdown
    app.before_serving(prime_db_pool)
    app.after_serving(close_db_pool)

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
