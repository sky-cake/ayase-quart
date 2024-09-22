from quart import flash, session
from quart_wtf import QuartForm
from wtforms import widgets
from wtforms.fields import (
    BooleanField,
    DateField,
    HiddenField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError
)

from configs import CONSTS
from db.api import get_user_with_username, is_correct_password
from enums import ReportCategory, ReportStatus, SearchMode, UserRole
from posts.capcodes import Capcode

LENGTH_MD5_HASH = 32


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class SearchForm(QuartForm):
    search_mode = RadioField('Search Mode', choices=[(SearchMode.index, SearchMode.index), (SearchMode.gallery, SearchMode.gallery)], default=SearchMode.index)
    order_by = RadioField('Order By', choices=[('asc', 'asc'), ('desc', 'desc')], default='desc')
    boards = MultiCheckboxField('Boards', choices=CONSTS.board_shortnames)
    result_limit = IntegerField('Result Limit', default=CONSTS.default_result_limit, validators=[NumberRange(1, CONSTS.max_result_limit)], description='Per board')
    title = StringField("Subject", validators=[Optional(), Length(2, 256)])
    comment = TextAreaField("Comment", validators=[Optional(), Length(2, 1024)])
    num = StringField("Post Number", validators=[Optional(), Length(2, 20)])
    media_filename = StringField("Filename", validators=[Optional(), Length(2, 256)])
    media_hash = StringField("File Hash", validators=[Optional(), Length(22, LENGTH_MD5_HASH)])
    date_after = DateField('Date after', validators=[Optional()], format='%Y-%m-%d')
    date_before = DateField('Date before', validators=[Optional()], format='%Y-%m-%d')
    has_file = BooleanField('Has File', default=False, validators=[Optional()])
    has_no_file = BooleanField('No file', default=False, validators=[Optional()])
    is_op = BooleanField('OP', default=False, validators=[Optional()])
    is_not_op = BooleanField('Not OP', default=False, validators=[Optional()])
    is_deleted = BooleanField('Deleted', default=False, validators=[Optional()])
    is_not_deleted = BooleanField('Not deleted', default=False, validators=[Optional()])
    is_sticky = BooleanField('Sticky', default=False, validators=[Optional()])
    is_not_sticky = BooleanField('Not sticky', default=False, validators=[Optional()])
    page = IntegerField(default=1, validators=[Optional()])
    width = IntegerField('Width', default=None, validators=[Optional(), NumberRange(0, 4_294_967_295)], description='Media resolution width')
    height = IntegerField('Height', default=None, validators=[Optional(), NumberRange(0, 4_294_967_295)], description='Media resolution height')
    capcode = SelectField('Capcode', default=Capcode.default.value, choices=[(cc.value, cc.name) for cc in Capcode], validate_choice=False)
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


async def validate_username_is_provided(form, field):
    username = form.username.data

    if username:
        form.username.data = username.strip()

    if not username:
        await flash('Please provide a username.', 'warning')
        raise ValidationError()


async def validate_login_user(form, field):
    """Login user should already exist."""

    username = form.username.data
    password_candidate = form.password.data

    user_record = get_user_with_username(username)

    if not user_record or not is_correct_password(user_record, password_candidate):
        await flash('Incorrect username or password.', 'warning')
        raise ValidationError()

    await flash('User logged in.', 'success')
    session['user_id'] = user_record['user_id']


class UserForm(QuartForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=1, max=512), validate_username_is_provided], render_kw={'placeholder': 'Username'})
    password = PasswordField('Password', validators=[DataRequired(), Length(min=1, max=512), validate_login_user], render_kw={'placeholder': 'Password'})
    active = BooleanField('Active', validators=[InputRequired()])
    role = RadioField('Role', validators=[DataRequired()], choices=((r, r) for r in UserRole))
    notes = TextAreaField('Notes', validators=[DataRequired()])
    # created_datetime
    # last_login_datetime
    submit = SubmitField('Submit')


class ReportForm(QuartForm):
    post_no = IntegerField('Post No.', validators=[NumberRange(min=0)])
    category = RadioField('Report Category', choices=((c, c) for c in ReportCategory))
    details = TextAreaField('Details', validators=[Optional()])
    status = RadioField('Status', choices=((s, s) for s in ReportStatus))
    # created_datetime
    # last_updated_datetime
    submit = SubmitField('Submit')
