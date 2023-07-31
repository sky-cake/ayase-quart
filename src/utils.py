import configs


def get_board_entry(board_name: str):
    """Find board in list of archives, if not check list of boards, otherwise return empty entry"""
    return next(
        (
            item
            for item in (configs.archive_list or [])
            if item["shortname"] == board_name
        ),
        next(
            (
                item
                for item in (configs.board_list or [])
                if item["shortname"] == board_name
            ),
            {"shortname": "", "name": ""},
        ),
    )
