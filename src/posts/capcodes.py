"""
Mostly for working with post capcodes in the search.
This is probably not the final home for module.
"""

from enum import StrEnum
from typing import Dict


class Capcode(StrEnum):
	user = ''
	founder = 'F'
	dev = 'D'
	admin = 'A'
	moderator = 'M'
	manager = 'G'
	verified = 'V'

capcode_ints = {
	Capcode.user: 0,
	Capcode.founder: 1,
	Capcode.dev: 2,
	Capcode.admin: 3,
	Capcode.moderator: 4,
	Capcode.manager: 5,
	Capcode.verified: 6,
}

# 0 reserved for any
def capcode_2_id(capcode: str|None) -> int:
	if capcode is None:
		return 0
	capcode = capcode.strip().upper()
	return capcode_ints.get(capcode, 0)


int_capcodes: Dict[int: str] = {v:k for k,v in capcode_ints.items()}
def id_2_capcode(capcode_id: int|None) -> str:
    if capcode_id not in int_capcodes:
        return None
    return int_capcodes.get(capcode_id, Capcode.user)