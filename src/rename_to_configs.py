from typing import List, Dict

# allow moderation of posts
mod_portal: bool = True

# mod credentials for login. Only functional if `mod_portal = True`
mod_username: str = "x"
mod_password: str = "x"

# md5, sha256
hash_format: str = 'md5'

site_name: str = 'Ayase Quart'

# get extra debugging hints
debug_mode: bool = True

# secret key for auth, change it when in production
SECRET_KEY: str = "0123456789"

archive_list: List[Dict[str, str]] = [
    {'shortname': 'ck', 'name': 'Food & Cooking'},
    {'shortname': 'g', 'name': 'Technology'},
]

# need to port over support from Ayase
board_list = []

# need to port over support from Ayase
default_skin: str = 'default'

image_location: Dict[str, str] = {
    'image': "/static/hayden_asagi/{board_name}/image",
    'thumb': "/static/hayden_asagi/{board_name}/thumb"
}


# Hayden instance - only mysql supported at the moment
database: Dict = {
    'default': 'mysql',
    'mysql': {
        'host': "127.0.0.1",
        'port': 3306,
        'db': "hayden_asagi",
        'user': "USER",
        'password': "PASSWORD",
        'charset': "utf8mb4",
        'min_connections': 2,
        'max_connections': 5,
    }
}




# Do not touch the below code. Thank you.

_archives: List[str] = []
for _archive in archive_list:
    _archives.append(_archive['shortname'])

_boards: List[str] = []
for _board in archive_list:
    _boards.append(_board['shortname'])

_options: Dict[str, bool] = {
    'post_selector': True,
    'stats': False,
    'ghost': False,
    'search': False,
    'reports': False,
    'moderation': False, # need to merge this with other mod config
}

_scraper = {
    'default': 'asagi',
    'asagi': {
        'source': "https://github.com/eksopl/asagi"
    },
}

_asagi: bool = True

render_constants = dict(
    mod_portal=mod_portal,
    site_name = site_name,
    skins = default_skin,
    sha256_dirs = hash_format=='sha256',
    asagi = _asagi,
    archives = archive_list,
    boards = board_list,
    options = _options,
    scraper = _scraper,
)
