from msgspec import Struct, Meta
from typing import Annotated

from quart import Blueprint, jsonify
from quart_schema import validate_querystring, validate_request

from ...boards import board_shortnames
from ...enums import ModStatus, PublicAccess, ReportAction
from ...moderation.auth import (
    login_api_usr_required,
    require_api_usr_is_active,
    require_api_usr_permissions
)
from ...moderation.report import get_reports, reports_action_routine
from ...moderation.user import Permissions, get_user_by_id


bp = Blueprint('bp_api_moderation', __name__, url_prefix='/api/v1')


BoardStr = Annotated[str, Meta(min_length=1, max_length=5)]
BoardList = Annotated[list[BoardStr], Meta(min_length=1, max_length=len(board_shortnames))]


class ReportGET(Struct):
    public_access: PublicAccess
    mod_status: ModStatus
    page_size: Annotated[int, Meta(gt=0, le=50)] = 20
    page_num: Annotated[int, Meta(gt=0)] = 0
    board_shortnames: BoardList | BoardStr = board_shortnames


@bp.get('/reports')
@validate_querystring(ReportGET)
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.report_read])
async def reports_get(query_args: ReportGET, current_api_usr_id: int):
    reports = await get_reports(
        public_access=query_args.public_access,
        mod_status=query_args.mod_status,
        board_shortnames=board_shortnames,
        page_num=query_args.page_num,
        page_size=query_args.page_size,
    )
    return jsonify(reports)


class ReportPOST(Struct):
    action: ReportAction
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
    report_parent_ids: Annotated[list[int], Meta(min_length=1)]


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
