from blueprints.api.bp_app import bp as bp_api_app
from blueprints.web.bp_about import bp as bp_about
from blueprints.web.bp_app import bp as bp_web_app
from configs import (
    archiveposting_conf,
    index_search_conf,
    media_conf,
    mod_conf,
    stats_conf,
    vanilla_search_conf,
    vox_conf
)

blueprints = [
    bp_about,
    bp_api_app, # the configurable (on/off) .json endpoints
    bp_web_app,
]


if index_search_conf['enabled']:
    from blueprints.web.bp_index_search import bp as bp_web_index_search
    blueprints += [bp_web_index_search]


if vanilla_search_conf['enabled']:
    from blueprints.web.bp_vanilla_search import bp as bp_web_vanilla_search
    blueprints += [bp_web_vanilla_search]


if vox_conf['enabled']:
    from blueprints.web.bp_vox import bp as bp_web_vox
    blueprints += [bp_web_vox]


if archiveposting_conf['enabled']:
    from blueprints.web.bp_archiveposting import bp as bp_web_archiveposting
    blueprints += [bp_web_archiveposting]


if mod_conf['enabled']:
    from blueprints.api.bp_admin import bp as bp_api_admin
    from blueprints.api.bp_auth import bp as bp_api_auth
    from blueprints.api.bp_moderation import bp as bp_api_moderation
    from blueprints.web.bp_admin import bp as bp_web_admin
    from blueprints.web.bp_auth import bp as bp_web_auth
    from blueprints.web.bp_moderation import bp as bp_web_moderation

    blueprints += [
        bp_web_auth,
        bp_api_auth,

        bp_web_admin,
        bp_api_admin,

        bp_web_moderation,
        bp_api_moderation,
    ]


if stats_conf['enabled']:
    from blueprints.web.bp_stats import bp as bp_web_stats
    blueprints += [
        bp_web_stats,
    ]


if media_conf.get('serve_outside_static'):
    from blueprints.web.bp_media import bp as bp_api_media
    blueprints += [
        bp_api_media, # media served from outside src/static
    ]
