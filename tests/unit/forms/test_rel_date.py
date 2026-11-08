from datetime import datetime, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import BadRequest

from wtforms import Form

# `ayase_quart.boards` connects to the database at import time.
# stub out so `ayase_quart.forms` can be imported without a live database.
import sys
import types
if 'ayase_quart.boards' not in sys.modules:
    boards_stub = types.ModuleType('ayase_quart.boards')
    boards_stub.boards = {}
    boards_stub.board_shortnames = ['a', 'b']
    boards_stub.board_objects = []
    sys.modules['ayase_quart.boards'] = boards_stub

from ayase_quart.forms import (  # noqa: E402
    REL_DATE_DAYS,
    REL_DATE_HOURS,
    REL_DATE_MONTHS,
    REL_DATE_PRESETS,
    REL_DATE_YEARS,
    SearchForm,
    compute_rel_date_cutoff,
)


class RelDateForm(Form):
    date_rel = SearchForm.date_rel


def test_presets_are_unique():
    assert len(REL_DATE_PRESETS) == len(set(REL_DATE_PRESETS))
    assert set(REL_DATE_PRESETS) == set(REL_DATE_HOURS) | set(REL_DATE_DAYS) | set(REL_DATE_MONTHS) | set(REL_DATE_YEARS) | {'ytd'}


def test_hours_preset_is_now_minus_hours():
    for preset, hours in REL_DATE_HOURS.items():
        before = int(datetime.now().timestamp()) - hours * 3600
        cutoff = compute_rel_date_cutoff(preset)
        after = int(datetime.now().timestamp()) - hours * 3600
        assert before <= cutoff <= after


def test_days_preset_is_midnight_minus_days():
    now = datetime.now()
    midnight = datetime(now.year, now.month, now.day)
    for preset, days in REL_DATE_DAYS.items():
        assert compute_rel_date_cutoff(preset) == int((midnight - timedelta(days=days)).timestamp())


def test_months_preset_is_midnight_minus_months():
    now = datetime.now()
    midnight = datetime(now.year, now.month, now.day)
    for preset, months in REL_DATE_MONTHS.items():
        assert compute_rel_date_cutoff(preset) == int((midnight - relativedelta(months=months)).timestamp())


def test_years_preset_is_midnight_minus_years():
    now = datetime.now()
    midnight = datetime(now.year, now.month, now.day)
    for preset, years in REL_DATE_YEARS.items():
        assert compute_rel_date_cutoff(preset) == int((midnight - relativedelta(years=years)).timestamp())


def test_ytd_preset_is_jan_first():
    now = datetime.now()
    assert compute_rel_date_cutoff('ytd') == int(datetime(now.year, 1, 1).timestamp())

def test_unknown_preset_raises():
    for preset in ('', '10h', 'forever', '1h '):
        with pytest.raises(BadRequest):
            compute_rel_date_cutoff(preset)


def test_unknown_preset_is_rejected_by_validate_search_form():
    form = RelDateForm(data={'date_rel': 'forever'})
    assert form.date_rel.data == 'forever'
    with pytest.raises(BadRequest):
        compute_rel_date_cutoff(form.date_rel.data)


def test_valid_preset_populates_date_after():
    form = RelDateForm(data={'date_rel': '1h'})
    cutoff = compute_rel_date_cutoff(form.date_rel.data)
    now = int(datetime.now().timestamp())
    assert now - 3600 - 2 <= cutoff <= now - 3600
