from enum import Enum
from quart import flash, session
from quart_wtf import QuartForm, FileSize, FileAllowed
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
    TextAreaField,
    FileField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)
from datetime import datetime
from boards import board_shortnames
from enums import SubmitterCategory
from moderation.user import Permissions, is_valid_creds
from posts.capcodes import Capcode
from configs import index_search_conf, vanilla_search_conf, tag_conf, archiveposting_conf
from utils.integers import clamp_positive_int
import re
from tagging.enums import SafeSearch
from collections import Counter


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

render_kw_hide = {'style': 'display: none;'}
hide_tag_field = None if tag_conf['enabled'] else render_kw_hide


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


class PostForm(StripForm):
    do_not_strip = []

    new_thread = BooleanField('New Thread')
    thread_num = IntegerField('Thread Num', validators=[Optional(), NumberRange(1, 1_000_000_000)])
    title = StringField('Subject', validators=[Length(0, 32)])
    comment = TextAreaField('Comment', validators=[Length(2, 2048)])

    captcha_id = HiddenField(validators=[DataRequired()])
    captcha_answer = IntegerField(validators=[DataRequired()])
    submit = SubmitField('Post')

    async def validate(self, extra_validators=None) -> bool:
        """Overriding this definition allows us to validate fields in a specific order, and halt on a validation error."""

        item_order = self._fields.keys()
        for item in item_order:
            field = self._fields[item]
            if not field.validate(self, tuple()):
                return False

        if archiveposting_conf['ascii_only'] and not self.title.data.isascii():
            raise BadRequest('ascii only')

        if archiveposting_conf['ascii_only'] and not self.comment.data.isascii():
            raise BadRequest('ascii only')

        self.title.data = collapse_newlines(strip_2_none(self.title.data))
        self.comment.data = collapse_newlines(strip_2_none(self.comment.data))

        if is_too_long(self.title.data) or is_too_long(self.comment.data):
            raise BadRequest('20 lines exceeded')

        if is_spam(self.title.data) or is_spam(self.comment.data):
            raise BadRequest('Our system thinks your post is spam')

        return True


class MessageForm(StripForm):
    do_not_strip = []
    title = StringField("Subject", validators=[Length(0, 128)])
    comment = TextAreaField("Comment", validators=[Length(2, 2048)])
    captcha_id = HiddenField(validators=[DataRequired()])
    captcha_answer = IntegerField("", validators=[DataRequired()])
    submit = SubmitField('Search')


def date_filter(x):
    return datetime.strptime(x, '%Y-%m-%d') if x and re.fullmatch(r'\d\d\d\d-\d\d-\d\d', x) else None


class SearchForm(StripForm):
    do_not_strip = ('comment',)

    boards: MultiCheckboxField | RadioField
    hits_per_page: IntegerField

    gallery_mode = BooleanField('Gallery Mode', default=False, validators=[Optional()])
    order_by = RadioField('Order By', choices=[('asc', 'asc'), ('desc', 'desc')], default='desc')
    title = StringField("Subject", validators=[Optional(), Length(2, 256)])
    comment = TextAreaField("Comment", validators=[Optional(), Length(2, 1024)])
    op_title = StringField("OP Subject", validators=[Optional(), Length(2, 256)], description='Search posts belonging to a thread matching this OP subject')
    op_comment = TextAreaField("OP Comment", validators=[Optional(), Length(2, 1024)], description='Search posts belonging to a thread matching this OP comment.')
    min_title_length = IntegerField('Subject', validators=[Optional(), NumberRange(0, 100)])
    min_comment_length = IntegerField('Comment', validators=[Optional(), NumberRange(0, 2_000)])
    num = IntegerField("Post Number", validators=[Optional(), NumberRange(min=0)])
    media_filename = StringField("Filename", validators=[Optional(), Length(2, 256)])
    media_hash = StringField("File Hash", validators=[Optional(), Length(22, LENGTH_MD5_HASH)])
    tripcode = StringField("Tripcode", validators=[Optional(), Length(8, 15)])
    date_after = DateField('Start', validators=[Optional()], format='%Y-%m-%d', filters=[date_filter])
    date_before = DateField('End', validators=[Optional()], format='%Y-%m-%d', filters=[date_filter])
    has_file = BooleanField('Has file', default=False, validators=[Optional()])
    has_no_file = BooleanField('No file', default=False, validators=[Optional()])

    safe_search = RadioField('Safe Search', choices=[(ss.value, ss.name) for ss in SafeSearch], default=SafeSearch.safe.value, validate_choice=True, render_kw=hide_tag_field)

    ## Values will come in as strings like '1,2,3,4,5' or ''. A fieldlist of integerfields was too complex, and added bandwidth; ints_from_csv_string() will be used to convert the strings
    ## These fields' `choices` will be generated with js
    file_tags_general   = StringField('File tags, general',   default='', validators=[Length(min=0, max=100)], render_kw=render_kw_hide)
    file_tags_character = StringField('File tags, character', default='', validators=[Length(min=0, max=100)], render_kw=render_kw_hide)

    if tag_conf['enabled'] and tag_conf['allow_file_search']:
        file_upload = FileField('File Search', validators=[FileAllowed(tag_conf['exts']), FileSize(min_size=1024, max_size=4.05 * 1024 * 1024)])

    is_op = BooleanField('OP', default=False, validators=[Optional()])
    is_not_op = BooleanField('Not OP', default=False, validators=[Optional()])
    is_deleted = BooleanField('Deleted', default=False, validators=[Optional()])
    is_not_deleted = BooleanField('Not deleted', default=False, validators=[Optional()])
    is_sticky = BooleanField('Sticky', default=False, validators=[Optional()])
    is_not_sticky = BooleanField('Not sticky', default=False, validators=[Optional()])
    page = IntegerField(default=1, validators=[NumberRange(min=1)])
    width = IntegerField('Media width', default=None, validators=[Optional(), NumberRange(0, 10_000)])
    height = IntegerField('Media height', default=None, validators=[Optional(), NumberRange(0, 10_000)])
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


# introduce fields in dervied classes when they depend on different search confs

class VanillaSearchForm(SearchForm):
    boards = MultiCheckboxField('Boards', choices=board_shortnames, validate_choice=True) if vanilla_search_conf['multi_board_search'] else RadioField('Board', choices=board_shortnames, default=board_shortnames[0], validate_choice=False)
    hits_per_page = IntegerField('Per page', default=vanilla_search_conf['hits_per_page'], validators=[NumberRange(1, vanilla_search_conf['hits_per_page'])], description='Per board')
    
    if vanilla_search_conf.get('use_file_archived'):
        file_archived = BooleanField('File Archived', default=False, validators=[Optional()])


class IndexSearchForm(VanillaSearchForm):
    boards = MultiCheckboxField('Boards', choices=board_shortnames, validate_choice=True) if index_search_conf['multi_board_search'] else RadioField('Board', choices=board_shortnames, default=board_shortnames[0], validate_choice=False)
    hits_per_page = IntegerField('Per page', default=index_search_conf['hits_per_page'], validators=[NumberRange(1, index_search_conf['hits_per_page'])], description='Per board')
    
    if index_search_conf.get('use_file_archived'):
        file_archived = BooleanField('File Archived', default=False, validators=[Optional()])


def strip_2_none(s: str) -> str | None:
    if not isinstance(s, str) or s.strip() == '':
        return None
    return s


def ints_from_csv_string(csv_string: str) -> list[int]:
    if not csv_string or not isinstance(csv_string, str):
        return []

    csv_string = csv_string.strip()
    if not re.fullmatch(r'^\d+(?:,\d+)*$', csv_string):
        return []

    return [int(i) for i in csv_string.split(',')]


def validate_search_form(form: SearchForm):
    # board validations should work with str and list[str]
    if not form.boards.data:
        raise BadRequest('select a board')

    if len(form.boards.data) < 1:
        raise BadRequest('select a board')

    if len(form.boards.data) > len(board_shortnames):
        raise BadRequest('too many boards selected')

    if not form.boards.validate_choice:
        if not isinstance(form.boards.data, list):
            raise ValueError(type(form.boards.data))
        for b in form.boards.data:
            if b not in board_shortnames:
                raise BadRequest('invalid board choice(s)')

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

    if tag_conf['enabled']:
        form.file_tags_general.data   = ints_from_csv_string(form.file_tags_general.data)
        form.file_tags_character.data = ints_from_csv_string(form.file_tags_character.data)

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
