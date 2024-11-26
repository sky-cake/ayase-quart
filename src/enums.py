from enum import Enum, StrEnum


class DbType(Enum):
    mysql = 1
    sqlite = 2


class SearchType(StrEnum):
    sql = 'sql'
    idx = 'idx'


class IndexSearchType(StrEnum):
    meili = 'meili'
    manticore = 'manticore'
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
    illegal_content = 'Illegal content'
    dcma = 'DCMA'
    underage = '18+ only'
    embedded_data = 'Media with embedded data'
    doxxing = 'Doxxing'
    work_safe = 'NSFW content on a SFW board'
    spamming = 'Spam or flooding'
    advertising = 'Advertising'
    impersonation = 'Impersonation'
    bots = 'Bots or scrapers'
    other = 'Other'
