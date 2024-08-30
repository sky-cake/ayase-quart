import quart_flask_patch  # isort: skip

import asyncio
import os

from flask_bootstrap import Bootstrap5
from hypercorn.middleware import ProxyFixMiddleware
from quart import Quart

from blueprint_admin import blueprint_admin
from blueprint_api import blueprint_api
from blueprint_app import blueprint_app
from blueprint_auth import blueprint_auth
from blueprint_moderation import blueprint_moderation
from blueprint_search import blueprint_search
from configs import CONSTS
from db import get_database_instance
from db.api import init_moderation_db
from limiter import limiter


if CONSTS.TESTING:
    import tracemalloc
    tracemalloc.start()


async def create_app():

    if CONSTS.chdir_to_root:
        os.chdir(CONSTS.root_dir)

    app = Quart(__name__)

    app.config.from_object(CONSTS)

    if CONSTS.using_proxy:
        # https://hypercorn.readthedocs.io/en/latest/how_to_guides/proxy_fix.html
        app.asgi_app = ProxyFixMiddleware(app.asgi_app, mode="legacy", trusted_hops=1)

    if CONSTS.redis_url:
        limiter.init_app(app)

    app.config['MATH_CAPTCHA_FONT'] = os.path.join(os.path.dirname(__file__), "fonts/tly.ttf")

    Bootstrap5(app)
    app.jinja_env.auto_reload = False

    app.register_blueprint(blueprint_api)
    app.register_blueprint(blueprint_app)
    app.register_blueprint(blueprint_admin)
    app.register_blueprint(blueprint_auth)
    app.register_blueprint(blueprint_search)
    app.register_blueprint(blueprint_moderation)

    app.db = get_database_instance()

    await init_moderation_db()

    # https://quart.palletsprojects.com/en/latest/how_to_guides/startup_shutdown.html#startup-and-shutdown
    app.before_serving(app.db.connect)
    app.after_serving(app.db.disconnect)

    return app


app = asyncio.run(create_app())

if __name__ == '__main__' and CONSTS.TESTING:
    app.run(CONSTS.site_host, port=CONSTS.site_port, debug=CONSTS.TESTING, certfile=CONSTS.cert_file, keyfile=CONSTS.key_file, use_reloader=CONSTS.TESTING and CONSTS.autoreload)
