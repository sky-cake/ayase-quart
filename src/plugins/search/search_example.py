# maintain syntax highlighting without loading this example
if 0:
    from forms import SearchForm
    from jinja2 import Template
    from templates import env
    from wtforms import Field, StringField
    from wtforms.validators import DataRequired

    from plugins.i_search import SearchPlugin, SearchPluginResult
    from utils import Perf


    # there must exist a class that implements SearchPlugin
    class SearchPluginExample(SearchPlugin):
        # you are responsible for any field name/id collisions
        fields: list[Field] = [
            StringField(label='sha256', name='sha256', id='sha256', validators=[DataRequired(message='Please enter a sha256sum.')]),
        ]

        # careful!
        # any html in this string WILL be rendered
        template: Template = env.from_string("""
            {% from 'macros/macros.html' import render_field %}
            <link rel="stylesheet" href="/static/plugins/example.css">
            {{render_field(form.sha256)}}
        """)

        async def get_search_plugin_result(self, form: SearchForm, p: Perf) -> SearchPluginResult:
            # perform your search based on the sha256 input...
            return SearchPluginResult() # .board_2_nums = {'g': set([1, 2, 3]), 'b': set([1, 3, 5])}
