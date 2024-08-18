from quart_wtf import QuartForm
from wtforms import widgets
from wtforms.fields import (
    BooleanField,
    DateField,
    HiddenField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField
)
from wtforms.validators import InputRequired, Length, NumberRange, Optional

from configs import CONSTS
from e_nums import SearchMode

LENGTH_MD5_HASH = 32


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class SearchForm(QuartForm):
    search_mode = RadioField('Search Mode', choices=[(SearchMode.index, SearchMode.index), (SearchMode.gallery, SearchMode.gallery)], default=SearchMode.index)
    order_by = RadioField('Order By', choices=[('asc', 'asc'), ('desc', 'desc')], default='desc')
    boards = MultiCheckboxField('Boards', choices=CONSTS.board_shortnames)
    result_limit = IntegerField('Result Limit', default=CONSTS.default_result_limit, validators=[NumberRange(1, CONSTS.max_result_limit)], description='Per board')
    title = StringField("Title", validators=[Optional(), Length(2, 256)])
    comment = TextAreaField("Comment", validators=[Optional(), Length(2, 1024)])
    num = StringField("Post Number", validators=[Optional(), Length(2, 20)])
    media_filename = StringField("Filename", validators=[Optional(), Length(2, 256)])
    media_hash = StringField("File Hash", validators=[Optional(), Length(22, LENGTH_MD5_HASH)])
    date_after = DateField('Date after', validators=[Optional()], format='%Y-%m-%d')
    date_before = DateField('Date before', validators=[Optional()], format='%Y-%m-%d')
    has_file = BooleanField('Post contains a file', default=False, validators=[Optional()])
    has_no_file = BooleanField('Post contains no file', default=False, validators=[Optional()])
    is_op = BooleanField('Is opening post (OP)', default=False, validators=[Optional()])
    is_not_op = BooleanField('Is not opening post (OP)', default=False, validators=[Optional()])
    is_deleted = BooleanField('Is deleted', default=False, validators=[Optional()])
    is_not_deleted = BooleanField('Is not deleted', default=False, validators=[Optional()])
    page = IntegerField(default=1, validators=[Optional()])
    submit = SubmitField('Search')


class IndexSearchConfigForm(QuartForm):
    boards = MultiCheckboxField('Boards', choices=CONSTS.board_shortnames)
    operation = RadioField(
        'Operation',
        choices=[
            ('init', 'Initialize a search index. This is board agnostic.'),
            ('populate', 'Populate the search index with data from selected board(s).'),
            ('wipe', 'Wipe all data from search index.'),
        ],
        default='init',
    )
    submit = SubmitField('Run')


class LoginForm(QuartForm):
    username = StringField(validators=[InputRequired(), Length(min=2, max=128)])
    password = PasswordField(validators=[InputRequired(), Length(min=2, max=128)])

    captcha_id = HiddenField(validators=[InputRequired()])
    captcha_answer = IntegerField("", validators=[InputRequired()])

    submit = SubmitField("Submit")
