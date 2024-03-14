from quart_wtf import QuartForm
from wtforms.fields import StringField, TextAreaField, SubmitField, SelectMultipleField, BooleanField, DateField
from wtforms.validators import Length, Optional
from wtforms import widgets
from configs import CONSTS

LENGTH_MD5_HASH = 32

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class SearchForm(QuartForm):
    boards = MultiCheckboxField('Boards', choices=CONSTS.board_shortnames)
    title = StringField("Title", validators=[Optional(), Length(2, 256)])
    comment = TextAreaField("Comment", validators=[Optional(), Length(2, 1024)])
    num = StringField("Post Number", validators=[Optional(), Length(2, 20)])
    media_filename = StringField("Filename", validators=[Optional(), Length(2, 256)])
    media_hash = StringField("File Hash", validators=[Optional(), Length(LENGTH_MD5_HASH, LENGTH_MD5_HASH)])
    date_after = DateField('Date after', validators=[Optional()], format='%Y-%m-%d')
    date_before = DateField('Date before', validators=[Optional()], format='%Y-%m-%d')
    has_file = BooleanField('Post contains a file', default=False, validators=[Optional()])
    has_no_file = BooleanField('Post contains no file', default=False, validators=[Optional()])
    is_op = BooleanField('Is opening post (OP)', default=False, validators=[Optional()])
    is_not_op = BooleanField('Is not opening post (OP)', default=False, validators=[Optional()])
    
    submit = SubmitField('Search')
