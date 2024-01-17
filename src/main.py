import os
from quart import Quart
from werkzeug.middleware.proxy_fix import ProxyFix
from configs import CONSTS
from blueprint_api import blueprint_api
from blueprint_app import blueprint_app
from blueprint_admin import blueprint_admin
from db import db_pool_open, db_pool_close

def create_app():

    if CONSTS.chdir_to_root:
        os.chdir(CONSTS.root_dir)

    app = Quart(__name__)

    app.config.from_object(CONSTS)

    app.register_blueprint(blueprint_api)
    app.register_blueprint(blueprint_app)
    app.register_blueprint(blueprint_admin)

    if CONSTS.REVERSE_PROXY:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # https://quart.palletsprojects.com/en/latest/how_to_guides/startup_shutdown.html#startup-and-shutdown
    app.before_serving(db_pool_open)
    app.after_serving(db_pool_close)

    return app


app = create_app()

app.run(CONSTS.site_host, port=CONSTS.site_port, debug=CONSTS.TESTING, certfile='cert.pem', keyfile='key.pem')
