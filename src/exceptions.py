import configs
from utils import get_board_entry


class NotFoundException(Exception):
    def __init__(self, board_name=configs.site_name):
        self.tab_title = board_name
        if board_name == configs.site_name:
            return
        board_description = get_board_entry(board_name)["name"]
        title = (
            f"/{board_name}/ - {board_description}" if board_description else board_name
        )
        self.tab_title = title


class QueryException(Exception):
    def __init__(self, error):
        self.tab_title = 'Error'
        self.debug_error = error
