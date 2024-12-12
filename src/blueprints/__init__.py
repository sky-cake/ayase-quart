from configs import media_conf

from .bp_admin import bp as bp_admin
from .bp_api import bp as bp_api
from .bp_app import bp as bp_app
from .bp_auth import bp as bp_auth
from .bp_media import bp as bp_media
from .bp_moderation import bp as bp_moderation
from .bp_search import bp as bp_search

blueprints = [
    bp_admin,
    bp_api,
    bp_app,
    bp_auth,
    bp_search,
    bp_moderation,
]

if media_conf.get('serve_outside_static'):
    blueprints += [bp_media]
