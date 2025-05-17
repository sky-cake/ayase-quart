from enum import Enum, StrEnum


class DbType(Enum):
    mysql = 1
    sqlite = 2
    postgres = 3


class SearchType(StrEnum):
    sql = 'sql'
    idx = 'idx'


class IndexSearchType(StrEnum):
    meili = 'meili'
    manticore = 'manticore'
    lnx = 'lnx'
    typesense = 'typesense'
    quickwit = 'quickwit'


class ModStatus(StrEnum):
    open = 'o'
    closed = 'c'


class PublicAccess(StrEnum):
    visible = 'v'
    hidden = 'h'


class ReportAction(StrEnum):
    report_delete = 'report_delete'
    post_delete = 'post_delete'
    media_delete = 'media_delete'
    media_hide = 'media_hide'
    media_show = 'media_show'
    post_show = 'post_show'
    post_hide = 'post_hide'
    report_close = 'report_close'
    report_open = 'report_open'
    report_save_notes = 'report_save_notes'


class SubmitterCategory(StrEnum):
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


class DbPool(Enum):
    main = 1
    mod = 2
