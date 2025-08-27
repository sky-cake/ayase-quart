from pydantic import BaseModel, Field
from quart import Blueprint, jsonify
from quart_schema import validate_querystring, validate_request

from boards import board_shortnames
from configs import archiveposting_conf
from enums import ModStatus, PublicAccess, ReportAction
from moderation.auth import (
    login_api_usr_required,
    require_api_usr_is_active,
    require_api_usr_permissions
)
from moderation.report import get_reports, reports_action_routine
from moderation.user import Permissions, get_user_by_id

bp = Blueprint('bp_api_moderation', __name__, url_prefix='/api/v1')


class ReportGET(BaseModel):
    public_access: PublicAccess = Field(None, description='v: visible, h: hidden')
    mod_status: ModStatus = Field(None, description='o: open, c: closed')
    page_size: int = Field(20, ge=0, le=50)
    page_num: int = Field(0, ge=0)
    board_shortnames: list[str] | str = Field(board_shortnames, min_items=0, max_items=len(board_shortnames))


@bp.get('/reports')
@validate_querystring(ReportGET)
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.report_read])
async def reports_get(query_args: ReportGET, current_api_usr_id: int):
    # query_args.board_shortnames if isinstance(query_args.board_shortnames, list) else [query_args.board_shortnames]
    bs = board_shortnames + [archiveposting_conf['board_name']] if archiveposting_conf['enabled'] else board_shortnames
    reports = await get_reports(
        public_access=query_args.public_access,
        mod_status=query_args.mod_status,
        board_shortnames=bs,
        page_num=query_args.page_num,
        page_size=query_args.page_size,
    )
    return jsonify(reports)

class ReportPOST(BaseModel):
    action: ReportAction = Field(f'One of: {[x.name for x in ReportAction]}')
    mod_notes: str | None = None


@bp.post('/reports/<int:report_parent_id>')
@validate_request(ReportPOST)
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.report_read])
async def reports_post(data: ReportPOST, current_api_usr_id: int, report_parent_id: int):
    current_api_usr = await get_user_by_id(current_api_usr_id)

    msg, code = await reports_action_routine(current_api_usr, report_parent_id, data.action, mod_notes=data.mod_notes)
    if code < 400:
        return {'msg': msg}, code
    return {'error': msg}, code


class ReportBulkPOST(ReportPOST):
    report_parent_ids: list[int] = Field(min_items=1)


@bp.post('/reports/bulk')
@validate_request(ReportBulkPOST)
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.report_read])
async def reports_action_bulk(data: ReportBulkPOST, current_api_usr_id: int):

    current_api_usr = await get_user_by_id(current_api_usr_id)

    results = {}
    codes = set()
    for report_parent_id in data.report_parent_ids:
        msg, code = await reports_action_routine(current_api_usr, report_parent_id, data.action, data.mod_notes)
        results[report_parent_id] = {'msg': msg, 'code': code}
        codes.add(code)

    if len(codes) == 0:
        return {}, 200
    elif len(codes) == 1:
        return results, code # last code of the loop

    return results, 207 # Multi-Status
