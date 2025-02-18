import quart_flask_patch

from collections import defaultdict
from dataclasses import dataclass
from quart_schema import validate_request, validate_response

from quart import Blueprint, flash, request
from boards import board_shortnames
from enums import ModStatus
from moderation.report import (
    get_reports_f,
    reports_action_routine
)
from moderation.user import Permissions, get_user_by_id
from moderation.auth import (
    login_api_usr_required,
    require_api_usr_is_active,
    require_api_usr_permissions
)


bp = Blueprint('bp_api_moderation', __name__, url_prefix='/api/v1')


@dataclass
class Token:
    token: str


@bp.get('/reports/closed')
@bp.get('/reports/closed/<int:page_num>')
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.report_read])
async def reports_closed(data: Token, current_api_usr_id: int, page_num: int=0):
    page_size = 20
    reports = await get_reports_f(mod_status=ModStatus.closed, board_shortnames=board_shortnames, page_num=page_num, page_size=page_size)
    # pagination = await make_report_pagination(ModStatus.closed, board_shortnames, len(reports), page_num, page_size=page_size)
    raise NotImplementedError


@bp.get('/reports/open')
@bp.get('/reports/open/<int:page_num>')
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.report_read])
async def reports_open(data: Token, current_api_usr_id: int, page_num: int=0):
    page_size=20
    reports = await get_reports_f(mod_status=ModStatus.open, board_shortnames=board_shortnames, page_num=page_num, page_size=page_size)
    # pagination = await make_report_pagination(ModStatus.open, board_shortnames, len(reports), page_num, page_size=page_size)
    raise NotImplementedError


@bp.post('/reports/<int:report_parent_id>/<string:action>')
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.report_read])
async def reports_action(data: Token, current_api_usr_id: int, report_parent_id: int, action: str):
    form = (await request.form)
    
    current_api_usr = await get_user_by_id(current_api_usr_id)

    msg = await reports_action_routine(current_api_usr, report_parent_id, action, mod_notes=form.get('mod_notes'))
    if msg:
        await flash(msg)

    raise NotImplementedError


@bp.post('/reports/bulk/<string:action>')
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.report_read])
async def reports_action_bulk(data: Token, current_api_usr_id: int, action: str):
    data = (await request.get_json())

    report_parent_ids = data.get('report_parent_ids', [])

    if not report_parent_ids:
        await flash('No reports submitted.')

    current_api_usr = await get_user_by_id(current_api_usr_id)

    msgs = defaultdict(lambda: 0)
    for report_parent_id in report_parent_ids:
        msg = await reports_action_routine(current_api_usr, report_parent_id, action)
        msgs[msg] += 1

    if msgs:
        await flash('<br>'.join([f'{msg} x{n}' for msg, n in msgs.items()]))

    raise NotImplementedError
