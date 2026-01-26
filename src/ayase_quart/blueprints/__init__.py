from .api.bp_app import bp as bp_api_app
from .web.bp_about import bp as bp_about
from .web.bp_app import bp as bp_web_app
from ..configs import (
    index_search_conf,
    media_conf,
    mod_conf,
    stats_conf,
    vanilla_search_conf,
)

blueprints = [
    bp_about,
    bp_api_app, # the configurable (on/off) .json endpoints
    bp_web_app,
]


if index_search_conf['enabled']:
    from .web.bp_search_fts import bp as bp_web_index_search
    blueprints += [bp_web_index_search]


if vanilla_search_conf['enabled']:
    from .web.bp_search_sql import bp as bp_web_vanilla_search
    blueprints += [bp_web_vanilla_search]


if mod_conf['enabled']:
    from .web.bp_admin import bp as bp_web_admin
    from .web.bp_auth import bp as bp_web_auth
    from .web.bp_moderation import bp as bp_web_moderation

    blueprints += [
        bp_web_auth,
        bp_web_admin,
        bp_web_moderation,
    ]


if mod_conf['enabled'] and mod_conf.get('api', False):
    from .api.bp_admin import bp as bp_api_admin
    from .api.bp_auth import bp as bp_api_auth
    from .api.bp_moderation import bp as bp_api_moderation

    blueprints += [
        bp_api_auth,
        bp_api_admin,
        bp_api_moderation,
    ]


if stats_conf['enabled']:
    from .web.bp_stats import bp as bp_web_stats
    blueprints += [
        bp_web_stats,
    ]


if media_conf.get('serve_outside_static'):
    from .web.bp_media import bp as bp_api_media
    blueprints += [
        bp_api_media, # media served from outside src/static
    ]
