import pathlib
import hashlib
import os
import base64
import json
from utils import make_src_path

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

def update_html_integrities(html_root: str, js_integrities: dict):
    html_root_path = pathlib.Path(html_root)
    for folder in set(p.parent for p in html_root_path.rglob('*.html') if p.is_file()):
        print('Scanning HTML directory:', folder.resolve())
    for html_file in html_root_path.rglob('*.html'):
        lines = html_file.read_text().splitlines()
        updated_lines = []
        changed = False
        for line in lines:
            if '<script' in line and 'src=' in line:
                for js_name, integrity in js_integrities.items():
                    if js_name in line:
                        changed = True
                        if 'integrity="' in line:
                            line = line[:line.find('integrity="')] + f'integrity="{integrity}"></script>'
                        else:
                            line = line.rstrip('>') + f' integrity="{integrity}">'
            updated_lines.append(line)
        if changed:
            html_file.write_text('\n'.join(updated_lines))

def make_path(*path):
    return os.path.join(os.path.dirname(__file__), *path)

def main():
    js_dir = make_path('static', 'js')
    html_dir = make_path('templates')

    assert os.path.isdir(js_dir)
    assert os.path.isdir(html_dir)

    integrities = collect_js_integrities(js_dir)
    # update_html_integrities(html_dir, integrities)
    with open(make_src_path('asset_hashes.json'), 'w') as f:
        json.dump(integrities, f)

if __name__ == '__main__':
    main()
