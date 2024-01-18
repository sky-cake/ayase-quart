from quart_wtf import QuartForm
from wtforms.fields import StringField, TextAreaField, SubmitField, SelectMultipleField, BooleanField, RadioField
from wtforms.validators import Length, Optional
from wtforms import widgets
from configs import CONSTS

LENGTH_MD5_HASH = 32

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

render_kw = {'style': "padding: 4px; margin: 4px; background-color: #282a2e; color: #c5c8c6; border: 1px solid black;"}
class SearchForm(QuartForm):
    # boards = MultiCheckboxField('Boards', choices=CONSTS.board_shortnames)
    boards = RadioField('Boards', choices=CONSTS.board_shortnames, default=CONSTS.board_shortnames[0], render_kw=render_kw)
    title = StringField("Title", validators=[Optional(), Length(1, 256)], render_kw=render_kw)
    comment = TextAreaField("Comment", validators=[Optional(), Length(1, 1024)], render_kw=render_kw)
    media_filename = StringField("Filename", validators=[Optional(), Length(1, 256)], render_kw=render_kw)
    media_hash = StringField("File Hash", validators=[Optional(), Length(LENGTH_MD5_HASH, LENGTH_MD5_HASH)], render_kw=render_kw)
    has_file = BooleanField('Post contains a file', default=False, validators=[Optional()], render_kw=render_kw)
    is_op = BooleanField('Is opening post (OP)', default=False, validators=[Optional()], render_kw=render_kw)
    
    submit = SubmitField('Search', render_kw=render_kw)
