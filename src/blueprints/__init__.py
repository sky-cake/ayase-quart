from .bp_admin import bp as admin_bp
from .bp_api import bp as api_bp
from .bp_app import bp as app_bp
from .bp_auth import bp as auth_bp
from .bp_search import bp as search_bp

blueprints = [
    admin_bp,
    api_bp,
    app_bp,
    auth_bp,
    search_bp,
]