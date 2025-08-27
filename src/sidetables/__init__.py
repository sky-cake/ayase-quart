from enum import StrEnum


class SideTableCmd(StrEnum):
    table_create = 'createtable'
    table_drop = 'droptable'
    table_backup = 'backuptable'
    index_add = 'addindex'
    index_drop = 'dropindex'
