from configs import media_conf, mod_conf

from blueprints.api.bp_app         import bp as bp_api_app
from blueprints.api.bp_auth        import bp as bp_api_auth

from blueprints.web.bp_admin       import bp as bp_web_admin
from blueprints.web.bp_app         import bp as bp_web_app
from blueprints.web.bp_auth        import bp as bp_web_auth
from blueprints.web.bp_media       import bp as bp_api_media
from blueprints.web.bp_moderation  import bp as bp_web_moderation
from blueprints.web.bp_search      import bp as bp_web_search

blueprints = [
    # js requests quotelink post previews using this bp, see `post_v()`
    bp_api_app,

    bp_web_admin,
    bp_web_app,
    bp_web_auth,
    bp_web_search,
]

if mod_conf['moderation']:
    blueprints += [bp_web_moderation, bp_api_auth]

if media_conf.get('serve_outside_static'):
    blueprints += [bp_api_media] # media served from outside src/static
