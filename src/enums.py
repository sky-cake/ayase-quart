from enum import Enum, StrEnum


class DbType(Enum):
    mysql = 1
    sqlite = 2


class SearchMode(StrEnum):
    index = 'index'
    gallery = 'gallery'


class IndexSearchType(StrEnum):
    meili = 'meili'
    manticore = 'manticore'
    mysql = 'mysql'
    lnx = 'lnx'
    typesense = 'typesense'
    quickwit = 'quickwit'


class UserRole(StrEnum):
    admin = "admin"
    moderator = "moderator"


class AuthActions(Enum):
    is_logged_in = 1
    log_in = 2
    log_out = 3

    get_user_id = 4

    is_admin = 5
    is_moderator = 6


class ReportStatus(StrEnum):
    open = "open"
    pending = "pending"
    closed = "closed"

class ReportCategory(StrEnum):
    doxxing = "doxxing"
    low_quality_content = "low_quality_content"
    illegal_content = "illegal_content"
