import quart_flask_patch  # isort: skip  # noqa: F401

import asyncio
import os

from flask_bootstrap import Bootstrap5
from quart import Quart

from blueprints import blueprints
from configs import QuartConfig, app_conf
from db import db_q
from moderation.mod import init_moderation_db
from templates import render_constants

# from security.limiter import limiter


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

    for bp in blueprints:
        app.register_blueprint(bp)

    await init_moderation_db()

    # https://quart.palletsprojects.com/en/latest/how_to_guides/startup_shutdown.html#startup-and-shutdown
    app.before_serving(db_q.prime_db_pool)
    app.after_serving(db_q.close_db_pool)

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
