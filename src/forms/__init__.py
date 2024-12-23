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
from enums import PostStatus, ReportCategory, ReportStatus, UserRole
from moderation.user import is_user_valid
from posts.capcodes import Capcode
from search import HITS_PER_PAGE
from utils.validation import clamp_positive_int, validate_board

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


class SearchForm(StripForm):
    do_not_strip = ('comment',)

    gallery_mode = BooleanField('Gallery Mode', default=False, validators=[Optional()])
    order_by = RadioField('Order By', choices=[('asc', 'asc'), ('desc', 'desc')], default='desc')
    boards = MultiCheckboxField('Boards', choices=board_shortnames)
    hits_per_page = IntegerField('Hits per page', default=HITS_PER_PAGE, validators=[NumberRange(1, HITS_PER_PAGE)], description='Per board')
    title = StringField("Subject", validators=[Optional(), Length(2, 256)])
    comment = TextAreaField("Comment", validators=[Optional(), Length(2, 1024)])
    op_title = StringField("OP Subject", validators=[Optional(), Length(2, 256)], description='Search posts belonging to a thread matching this OP subject')
    op_comment = TextAreaField("OP Comment", validators=[Optional(), Length(2, 1024)], description='Search posts belonging to a thread matching this OP comment.')
    num = IntegerField("Post Number", validators=[Optional(), NumberRange(min=0)])
    media_filename = StringField("Filename", validators=[Optional(), Length(2, 256)])
    media_hash = StringField("File Hash", validators=[Optional(), Length(22, LENGTH_MD5_HASH)])
    tripcode = StringField("Tripcode", validators=[Optional(), Length(8, 15)])
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
    page = IntegerField(default=1, validators=[NumberRange(min=1)])
    width = IntegerField('Width', default=None, validators=[Optional(), NumberRange(0, 4_294_967_295)], description='Media resolution width')
    height = IntegerField('Height', default=None, validators=[Optional(), NumberRange(0, 4_294_967_295)], description='Media resolution height')
    capcode = SelectField('Capcode', default=Capcode.default.value, choices=[(cc.value, cc.name) for cc in Capcode], validate_choice=False)
    submit = SubmitField('Search')

    async def validate(self, extra_validators=None) -> bool:
        """Overriding this definition allows us to validate fields in a specific order, and halt on a validation error."""
        
        validate_search_form(self) # call our custom validation

        item_order = self._fields.keys()
        for item in item_order:
            field = self._fields[item]
            if not field.validate(self, tuple()):
                return False
        return True


def strip_2_none(s: str) -> str|None:
    if isinstance(s, str) and s.strip() == '':
        return None
    return s


def validate_search_form(form: SearchForm):
    if not form.boards.data:
        raise BadRequest('select a board')

    for board in form.boards.data:
        validate_board(board)

    if form.gallery_mode.data and form.has_no_file.data:
        raise BadRequest("search gallery mode only shows files")

    if form.order_by.data not in ['asc', 'desc']:
        raise BadRequest('order_by is unknown')

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

    # if (form.op_comment.data or form.op_title.data) and (len(form.boards.data) > 1):
    #     raise BadRequest('faceted search is only available for a single board per search query at the moment')


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

    captcha_id = HiddenField(validators=[DataRequired()])
    captcha_answer = IntegerField("", validators=[DataRequired()])

    submit = SubmitField("Submit")


def enum_choices(enum_cls: Enum):
    return [(member.value, member.name) for member in enum_cls]


def enum_validator(enum_cls: Enum):
    def validator(form: QuartForm, field: Field):
        try:
            enum_cls(field.data)
        except ValueError:
            raise ValidationError(f"Invalid choice. Must be one of: {', '.join([e.value for e in enum_cls])}")
    return validator


class UserCreateForm(QuartForm):
    username = StringField('Username', default='admin', validators=[DataRequired(), Length(min=1, max=512)], render_kw={'placeholder': 'Username'})
    password = PasswordField('Password', default='admin', validators=[DataRequired(), Length(min=1, max=512)], render_kw={'placeholder': 'Password'})
    active = BooleanField('Active', validators=[DataRequired()])
    role = RadioField('Role', validators=[DataRequired()], choices=[(r, r) for r in UserRole])
    notes = TextAreaField('Notes', validators=[Optional(), Length(min=0, max=1024)])
    submit = SubmitField('Submit')

    async def async_validate_username(self, field):
        if self.username.data:
            self.username.data = self.username.data.strip()

        if not self.username.data:
            await flash('Please provide a username.', 'warning')
            raise ValidationError()
        
    async def async_validate_password(self, field):
        """Login user should already exist."""

        username = self.username.data
        password_candidate = self.password.data

        if not (user := await is_user_valid(username, password_candidate)):
            await flash('Incorrect username or password.', 'warning')
            raise ValidationError()

        await flash('User logged in.', 'success')
        session['user_id'] = user['user_id']


class UserEditForm(QuartForm):
    password_cur = PasswordField('Current Password', validators=[DataRequired(), Length(min=1, max=512)], render_kw={'placeholder': 'Password'})
    password_new = PasswordField('New Password', validators=[Length(min=0, max=512)], render_kw={'placeholder': 'Password'})
    active = BooleanField('Active', validators=[Optional()])
    role = RadioField('Role', validators=[DataRequired()], choices=[(r, r) for r in UserRole])
    notes = TextAreaField('Notes', validators=[Optional(), Length(min=0, max=1024)])
    submit = SubmitField('Submit')

    # raise RuntimeError('this validation does not work https://quart-wtf.readthedocs.io/en/latest/how_to_guides/form.html#async-custom-validators')
    async def async_validators_password_new(self, field):
        password_cur = self.password_cur.data
        password_new = self.password_new.data
        if password_new and password_cur == password_new:
            await flash('That\'s the same password.', 'warning')
            raise ValidationError()


class ReportUserForm(QuartForm):
    report_category = RadioField('Report Category', choices=enum_choices(ReportCategory), validators=[DataRequired(), enum_validator(ReportCategory)])
    submitter_notes = TextAreaField('Submitter Notes', validators=[Optional(), Length(min=0, max=512)])
    submit = SubmitField('Submit')


class ReportModForm(QuartForm):
    post_status = RadioField('Post Status', choices=enum_choices(PostStatus), validators=[DataRequired(), enum_validator(PostStatus)])
    report_status = RadioField('Report Status', choices=enum_choices(ReportStatus), validators=[DataRequired(), enum_validator(ReportStatus)])
    moderator_notes = TextAreaField('Moderator Notes', validators=[Optional(), Length(min=0, max=512)])
    submit = SubmitField('Submit')
