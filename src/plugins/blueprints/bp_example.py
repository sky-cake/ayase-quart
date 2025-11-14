# maintain syntax highlighting without loading this example
if 0:
    from quart import Blueprint

    # this module must have a Blueprint named bp
    # static_folder is relative to this module
    # static_url_path cannot be '/static'
    bp = Blueprint('bp_example', __name__, static_folder='../static', static_url_path='/static/plugins',)


    # you are responsible for any endpoint collisions
    @bp.get('/health_plugin_blueprint')
    async def health_plugin_blueprint():
        return '<link rel="stylesheet" href="/static/plugins/example.css"> ok', 200
