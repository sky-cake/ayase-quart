import quart_flask_patch  # isort: skip

import os

from flask_bootstrap import Bootstrap5
from quart import Quart
from werkzeug.middleware.proxy_fix import ProxyFix

from blueprint_admin import blueprint_admin
from blueprint_api import blueprint_api
from blueprint_app import blueprint_app
from blueprint_search import blueprint_search
from configs import CONSTS
from db import get_database_instance


def create_app():

    if CONSTS.chdir_to_root:
        os.chdir(CONSTS.root_dir)

    app = Quart(__name__)
    
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.keep_trailing_newline = False

    app.config.from_object(CONSTS)

    Bootstrap5(app)

    app.register_blueprint(blueprint_api)
    app.register_blueprint(blueprint_app)
    app.register_blueprint(blueprint_admin)
    app.register_blueprint(blueprint_search)


    if CONSTS.REVERSE_PROXY:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.db = get_database_instance()

    # https://quart.palletsprojects.com/en/latest/how_to_guides/startup_shutdown.html#startup-and-shutdown
    app.before_serving(app.db.connect)
    app.after_serving(app.db.disconnect)

    return app


app = create_app()

if __name__=='__main__':
    app.run(CONSTS.site_host, port=CONSTS.site_port, debug=CONSTS.TESTING, certfile=CONSTS.cert_file, keyfile=CONSTS.key_file, use_reloader=CONSTS.TESTING and CONSTS.autoreload)