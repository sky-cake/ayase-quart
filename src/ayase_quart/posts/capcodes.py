"""
Mostly for working with post capcodes in the search.
This is probably not the final home for module.
"""

from enum import StrEnum


class Capcode(StrEnum):
    any = 'any'
    user = 'N'
    founder = 'F'
    dev = 'D'
    admin = 'A'
    moderator = 'M'
    manager = 'G'
    verified = 'V'

    def from_str(capcode_str: str):
        try:
            return Capcode[capcode_str.strip().upper()]
        except Exception:
            return Capcode.user


capcode_ints = {
    Capcode.user: 0,
    Capcode.founder: 1,
    Capcode.dev: 2,
    Capcode.admin: 3,
    Capcode.moderator: 4,
    Capcode.manager: 5,
    Capcode.verified: 6,
}

def capcode_2_id(capcode: str) -> int:
    capcode = capcode.strip().upper()
    return capcode_ints.get(capcode, 0)


int_capcodes: dict[int, Capcode] = {v:k for k,v in capcode_ints.items()}
def id_2_capcode(capcode_id: int) -> Capcode:
    return int_capcodes.get(capcode_id, Capcode.user)
