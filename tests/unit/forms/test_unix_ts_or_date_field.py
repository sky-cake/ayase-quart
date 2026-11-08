import sys
import types
from datetime import datetime

from wtforms import Form
from wtforms.validators import NumberRange, Optional

# `ayase_quart.boards` connects to the database at import time.
# stub out so `ayase_quart.forms` can be imported without a live database.
if 'ayase_quart.boards' not in sys.modules:
    boards_stub = types.ModuleType('ayase_quart.boards')
    boards_stub.boards = {}
    boards_stub.board_shortnames = ['a', 'b']
    boards_stub.board_objects = []
    sys.modules['ayase_quart.boards'] = boards_stub

from ayase_quart.forms import UnixTsOrDateField  # noqa: E402


class UnixTsOrDateForm(Form):
    date_after = UnixTsOrDateField(validators=[Optional(), NumberRange(min=0)])
    date_before = UnixTsOrDateField(end_of_day=True, validators=[Optional(), NumberRange(min=0)])


def make_form(data: dict) -> Form:
    return UnixTsOrDateForm(data=data)


def test_date_string_after_is_start_of_day():
    form = make_form({'date_after': '2026-11-07'})
    assert form.date_after.data == int(datetime(2026, 11, 7).timestamp())


def test_date_string_before_is_end_of_day():
    form = make_form({'date_before': '2026-11-07'})
    assert form.date_before.data == int(datetime(2026, 11, 7, 23, 59, 59).timestamp())


def test_same_day_range_is_not_contradicted():
    form = make_form({'date_after': '2026-11-07', 'date_before': '2026-11-07'})
    assert form.date_after.data <= form.date_before.data


def test_unix_timestamp_passthrough():
    form = make_form({'date_after': '1731000000'})
    assert form.date_after.data == 1731000000

    form = make_form({'date_after': 1731000000})
    assert form.date_after.data == 1731000000


def test_missing_and_blank_values_are_none():
    for data in ({}, {'date_after': None}, {'date_after': ''}, {'date_after': '   '}):
        form = make_form(data)
        assert form.date_after.data is None
        assert form.date_before.data is None


def test_padded_date_string_is_accepted():
    form = make_form({'date_after': '  2026-11-07  '})
    assert form.date_after.data == int(datetime(2026, 11, 7).timestamp())


def test_malformed_date_string_is_a_field_error():
    form = make_form({'date_before': '2026-13-45'})
    assert form.date_before.data is None
    assert form.date_before.process_errors

    # strptime is lenient
    form = make_form({'date_after': '2026-11-7'})
    assert form.date_after.data == int(datetime(2026, 11, 7).timestamp())


def test_garbage_input_degrades_to_none():
    form = make_form({'date_after': 'abc'})
    assert form.date_after.data is None
    assert form.date_after.process_errors


def test_negative_timestamp_is_rejected():
    form = make_form({'date_after': '-5'})
    assert form.date_after.data is None
    assert form.date_after.process_errors


def test_valid_form_still_validates():
    form = make_form({'date_after': '2026-11-07', 'date_before': '2026-11-08'})
    assert form.validate() is True
