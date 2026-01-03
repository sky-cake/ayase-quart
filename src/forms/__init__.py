import re
from collections import Counter
from datetime import datetime
from enum import Enum

from quart import flash, session
from quart_wtf import QuartForm
from werkzeug.exceptions import BadRequest
from wtforms import widgets
from wtforms.fields import (
    BooleanField,
    DateField,
    Field,
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
    Length,
    NumberRange,
    Optional,
    ValidationError
)

from boards import board_shortnames
from configs import index_search_conf, vanilla_search_conf
from enums import SubmitterCategory
from moderation.user import Permissions, is_valid_creds
from posts.capcodes import Capcode
from utils.integers import clamp_positive_int

LENGTH_MD5_HASH = 32


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class StripForm(QuartForm):
    """Strips whitespace from all submitted `str` fields unless in `do_not_strip`."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self._fields.values():
            if isinstance(field, Field) and hasattr(field.data, 'strip') and (field.name not in self.do_not_strip):
                field.data = field.data.strip()


def is_spam(s) -> bool:
    if not s:
        return False

    words = s.lower().split()
    if not words:
        return False

    if len(words) < 10:
        return False

    # check if word is 60% or more of the words
    counts = Counter(words)
    total = len(words)

    for word, count in counts.items():
        if count / total >= 0.6:
            return True

    return False


def collapse_newlines(s):
    return re.sub(r'(\r\n){2,}|(\n){2,}', '\n', s) if s else s


def is_too_long(s: str):
    return s.count('\n') > 20 if s else False


def date_filter(x):
    return datetime.fromisoformat(x) if x else None


class MultiCheckboxCSVField(MultiCheckboxField):
    def process_data(self, data: str):
        if data is None:
            self.data = None
            return

        self.data = [v.strip() for v in data.split(',') if v.strip()]


class RadioCSVField(RadioField):
    def process_data(self, data: str):
        if data is None:
            self.data = None
            return

        d = [v.strip() for v in data.split(',') if v.strip()]
        if d:
            self.data = d[0]
            return

        self.data = None


valid_numeric_cmp_choices = [('=', '='), ('>', '>'), ('<', '<'), ('>=', '>='), ('<=', '<=')]
class SearchForm(StripForm):
    do_not_strip: tuple[str] = ('comment',)

    boards: MultiCheckboxCSVField | RadioCSVField
    hits_per_page: IntegerField

    gallery_mode = BooleanField('Gallery Mode', default=False, validators=[Optional()])
    order_by = RadioField('Order By', default=None, choices=[('asc', 'asc'), ('desc', 'desc')], validate_choice=False)
    title = StringField('Subject', validators=[Optional(), Length(2, 256)])
    comment = StringField('Comment', validators=[Optional(), Length(2, 1024)])
    op_title = StringField('OP Subject', validators=[Optional(), Length(2, 256)], description='Search posts belonging to a thread matching this OP subject')
    op_comment = StringField('OP Comment', validators=[Optional(), Length(2, 1024)], description='Search posts belonging to a thread matching this OP comment.')
    tl = IntegerField('Subject', validators=[Optional(), NumberRange(0, 100)])
    tlop = SelectField('Subject cmp', default=None, choices=valid_numeric_cmp_choices, validate_choice=False)
    cl = IntegerField('Comment', validators=[Optional(), NumberRange(0, 2_000)])
    clop = SelectField('Comment cmp', default=None, choices=valid_numeric_cmp_choices, validate_choice=False)
    num = IntegerField('Post Number', validators=[Optional(), NumberRange(min=0)])
    media_filename = StringField('Filename', validators=[Optional(), Length(2, 256)])
    media_hash = StringField('File Hash', validators=[Optional(), Length(22, LENGTH_MD5_HASH)])
    tripcode = StringField('Tripcode', validators=[Optional(), Length(8, 15)])
    date_after = DateField('Start', validators=[Optional()], format='%Y-%m-%d', filters=[date_filter])
    date_before = DateField('End', validators=[Optional()], format='%Y-%m-%d', filters=[date_filter])
    has_file = BooleanField('Has file', default=False, validators=[Optional()])
    has_no_file = BooleanField('No file', default=False, validators=[Optional()])

    is_op = BooleanField('OP', default=False, validators=[Optional()])
    is_not_op = BooleanField('Not OP', default=False, validators=[Optional()])
    is_deleted = BooleanField('Deleted', default=False, validators=[Optional()])
    is_not_deleted = BooleanField('Not deleted', default=False, validators=[Optional()])
    is_sticky = BooleanField('Sticky', default=False, validators=[Optional()])
    is_not_sticky = BooleanField('Not sticky', default=False, validators=[Optional()])
    page = IntegerField(default=1, validators=[NumberRange(min=1)])
    width = IntegerField('Media width', default=None, validators=[Optional(), NumberRange(0, 10_000)])
    wop = SelectField('Width cmp', default=None, choices=valid_numeric_cmp_choices, validate_choice=False)
    height = IntegerField('Media height', default=None, validators=[Optional(), NumberRange(0, 10_000)])
    hop = SelectField('Height cmp', default=None, choices=valid_numeric_cmp_choices, validate_choice=False)
    capcode = SelectField('Capcode', default=None, choices=[(cc.value, cc.name) for cc in Capcode], validate_choice=False)
    submit = SubmitField('Search')

    async def validate(self, extra_validators=None) -> bool:
        """Overriding this definition allows us to validate fields in a specific order, and halt on a validation error."""

        validate_search_form(self) # call our custom validation

        item_order = self._fields.keys()
        for item in item_order:
            field = self._fields[item]
            if not field.validate(self):
                return False
        return True


class SearchFormSQL(SearchForm):
    if vanilla_search_conf['multi_board_search']:
        boards = MultiCheckboxCSVField('Boards', choices=board_shortnames, validate_choice=True)
    else:
        boards = RadioCSVField('Board', choices=board_shortnames, validate_choice=True)

    hits_per_page = IntegerField('Per page', validators=[Optional(), NumberRange(1, per_page := vanilla_search_conf['hits_per_page'])], description=f'Per board max {per_page}')


class SearchFormFTS(SearchFormSQL):
    if index_search_conf['multi_board_search']:
        boards = MultiCheckboxCSVField('Boards', choices=board_shortnames, validate_choice=True)
    else:
        boards = RadioCSVField('Board', choices=board_shortnames, validate_choice=True)

    hits_per_page = IntegerField('Per page', validators=[Optional(), NumberRange(1, per_page := index_search_conf['hits_per_page'])], description=f'Per board max {per_page}')


def strip_2_none(s: str) -> str | None:
    if not isinstance(s, str) or s.strip() == '':
        return None
    return s


valid_numeric_cmp_operators = ('=', '>', '<', '>=', '<=')
def validate_search_form(form: SearchForm):
    if not (boards := form.boards.data):
        raise BadRequest('select a board')

    if len(form.boards.data) < 1:
        raise BadRequest('select a board')

    if isinstance(boards, str):
        # radio buttons makes form.boards.data str instead of list[str]
        boards = [boards]

    if len(boards) > len(board_shortnames):
        raise BadRequest('too many boards selected')

    if not form.boards.validate_choice:
        if not isinstance(form.boards.data, list):
            raise ValueError(type(form.boards.data))
        for b in form.boards.data:
            if b not in board_shortnames:
                raise BadRequest('invalid board choice(s)')

    if form.gallery_mode.data and form.has_no_file.data:
        raise BadRequest("search gallery mode only shows files")

    if form.is_op.data and form.is_not_op.data:
        raise BadRequest('is_op is contradicted')

    if form.is_deleted.data and form.is_not_deleted.data:
        raise BadRequest('is_deleted is contradicted')

    if form.is_sticky.data and form.is_not_sticky.data:
        raise BadRequest('is_sticky is contradicted')

    if form.date_before.data and form.date_after.data and (form.date_before.data < form.date_after.data):
        raise BadRequest('the dates are contradicted')

    form.comment.data = strip_2_none(form.comment.data)
    form.title.data = strip_2_none(form.title.data)
    form.op_comment.data = strip_2_none(form.op_comment.data)
    form.op_title.data = strip_2_none(form.op_title.data)

    form.page.data = clamp_positive_int(form.page.data, 1)

    if form.gallery_mode.data:
        form.has_file.data = True
        form.has_no_file.data = False

    if form.width.data and form.wop.data and form.wop.data not in valid_numeric_cmp_operators:
        form.wop.data = '='
    if form.height.data and form.hop.data and form.hop.data not in valid_numeric_cmp_operators:
        form.hop.data = '='
    if form.tl.data and form.tlop.data and form.tlop.data not in valid_numeric_cmp_operators:
        form.tlop.data = '='
    if form.cl.data and form.clop.data and form.clop.data not in valid_numeric_cmp_operators:
        form.clop.data = '='


class IndexSearchConfigForm(QuartForm):
    boards = MultiCheckboxField('Boards', choices=board_shortnames)
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
    username = StringField(validators=[DataRequired(), Length(min=1, max=128)])
    password = PasswordField(validators=[DataRequired(), Length(min=1, max=128)])
    captcha_id = HiddenField('', validators=[DataRequired()])
    captcha_answer = IntegerField('', validators=[DataRequired()])
    submit = SubmitField('Submit')


def enum_choices(enum_cls: Enum):
    return [(member.value, member.name) for member in enum_cls]


def enum_validator(enum_cls: Enum):
    def validator(form: QuartForm, field: Field):
        try:
            enum_cls(field.data)
        except ValueError:
            raise ValidationError(f"Invalid choice. Must be one of: {', '.join([e.value for e in enum_cls])}")
    return validator


class CSRFForm(QuartForm):
    pass


class UserBaseForm(QuartForm):
    is_admin = BooleanField('Is Admin', validators=[Optional()])
    permissions = MultiCheckboxField('Permissions', choices=enum_choices(Permissions), validators=[Optional()])
    is_active = BooleanField('Active', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(min=0, max=1024)])
    submit = SubmitField('Submit')

    async def async_validators_permissions(self, field):
        if self.permissions.data:
            self.permissions.data = [Permissions(p) for p in self.permissions.data]


class UserCreateForm(UserBaseForm):
    username = StringField('Username', default='admin', validators=[DataRequired(), Length(min=1, max=512)], render_kw={'placeholder': 'Username'})
    password = PasswordField('Password', default='admin', validators=[DataRequired(), Length(min=1, max=512)], render_kw={'placeholder': 'Password'})

    async def async_validators_username(self, field):
        if self.username.data:
            self.username.data = self.username.data.strip()

        if not self.username.data:
            await flash('Please provide a username.', 'warning')
            raise ValidationError()


class UserEditForm(UserBaseForm):
    password_cur = PasswordField('Current Password', validators=[DataRequired(), Length(min=1, max=512)], render_kw={'placeholder': 'Password'})
    password_new = PasswordField('New Password', validators=[Length(min=0, max=512)], render_kw={'placeholder': 'Password'})

    # raise RuntimeError('this validation does not work https://quart-wtf.readthedocs.io/en/latest/how_to_guides/form.html#async-custom-validators')
    async def async_validators_password_new(self, field):
        password_cur = self.password_cur.data
        password_new = self.password_new.data
        if password_new and password_cur == password_new:
            await flash('That\'s the same password.', 'warning')
            raise ValidationError()

    async def async_validators_password(self, field):
        """Login user should already exist."""

        username = self.username.data
        password_candidate = self.password.data

        if not (user := await is_valid_creds(username, password_candidate)):
            await flash('Incorrect username or password.', 'warning')
            raise ValidationError()

        await flash('User logged in.', 'success')
        session['user_id'] = user['user_id']


class ReportUserForm(QuartForm):
    submitter_category = RadioField('Report Category', choices=enum_choices(SubmitterCategory), validators=[DataRequired(), enum_validator(SubmitterCategory)])
    submitter_notes = TextAreaField('Submitter Notes', validators=[Optional(), Length(min=0, max=512)])
    submit = SubmitField('Submit')
