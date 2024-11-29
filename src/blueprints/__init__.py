from .bp_admin import bp as bp_admin
from .bp_api import bp as bp_api
from .bp_app import bp as bp_app
from .bp_auth import bp as bp_auth
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