from argparse import Namespace
import pathlib
import hashlib
import os
import base64

def calculate_integrity(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        digest = hashlib.sha384(f.read()).digest()
    return 'sha384-' + base64.b64encode(digest).decode()

def collect_js_integrities(js_root: str) -> dict:
    js_root_path = pathlib.Path(js_root)
    integrities = {}
    for folder in set(p.parent for p in js_root_path.rglob('*.js') if p.is_file()):
        print('Scanning JS directory:', folder.resolve())
    for js_file in js_root_path.rglob('*.js'):
        if js_file.is_file():
            integrities[js_file.name] = calculate_integrity(js_file)
    return integrities

def make_path(*path):
    return os.path.join(os.path.dirname(__file__), *path)

def prep_cli(args: Namespace) -> None:
    match args.cmd_1:
        case 'secret':
            from secrets import token_hex;
            from ..configs.conf_loader import CONF_FILE
            default_secret = 'DEFAULT_CHANGE_ME'
            try:
                with open(CONF_FILE, ) as f:
                    conf_data = f.read()
            except Exception as e:
                print(e)
                return
            if not default_secret in conf_data:
                print('No default secret found')
                return
            new_secret = token_hex(24)
            print(new_secret)
            with open(CONF_FILE, 'w') as f:
                f.write(conf_data.replace(default_secret, new_secret))
        case 'hashjs':
            import json
            js_dir = make_path('..', 'static', 'js')
            integrities = collect_js_integrities(js_dir)
            with open(make_path('./asset_hashes.json'), 'w') as f:
                json.dump(integrities, f, indent=4)
        case 'boards':
            from ..boards import validate_boards_in_db
            validate_boards_in_db()
            print('ok')
        case 'filtercache':
            import asyncio
            from ..moderation import fc
            asyncio.run(fc._create_cache())
