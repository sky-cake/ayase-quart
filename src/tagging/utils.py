import hashlib
import os
import shlex
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Generator
import base64
import re


def get_board_filename_pair_from_image_path(image_path: str):
    m = re.match(r'.*\/(?P<board>[a-z0-9]{1,4})\/image\/\d{4}\/\d{2}\/(?P<filename>.*)', image_path)
    if m:
        return m.group('board'), m.group('filename')
    return None


def is_valid_path(path: str) -> bool:
    return all(char.isalnum() or char in ('-', '_', '.', '/') for char in os.path.basename(path))


def get_image_file_count(directory: str, extensions: list[str]) -> int:
    """Provide extensions like .ext"""
    if not os.path.isdir(directory):
        raise ValueError('Provided path is not a directory')
    if not is_valid_path(directory):
        raise ValueError('Directory includes bad characters.')
    find_extensions = " -o ".join(f"-iname '*{ext}'" for ext in extensions)
    command = f'find {shlex.quote(directory)} -type f \\( {find_extensions} \\) | wc -l'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return int(result.stdout.strip())


def get_torch_device(cpu: bool):
    from torch import cuda, device
    if cpu:
        return device('cpu')
    return device('cuda' if cuda.is_available() else 'cpu')


def get_sha256_from_path(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65_536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_base64_md5_from_path(file_path):
    """https://github.com/4chan/4chan-API/blob/master/pages/Threads.md"""
    try:
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as file:
            for chunk in iter(lambda: file.read(65_536), b''):
                md5_hash.update(chunk)
        return base64.b64encode(md5_hash.digest()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def get_sha256_from_bytesio(bytes_io: BytesIO) -> str:
    hasher = hashlib.sha256()
    for chunk in iter(lambda: bytes_io.read(65536), b""):
        hasher.update(chunk)
    return hasher.hexdigest()


def get_sha256_from_bytesio_and_write(image_path: str, bytes_io: BytesIO) -> str:
    hasher = hashlib.sha256()

    with open(image_path, mode='wb') as f:
        for chunk in iter(lambda: bytes_io.read(16_384), b""):
            f.write(chunk)
            hasher.update(chunk)

    return hasher.hexdigest()


def make_path(*filepaths):
    """Make a path relative to this file."""
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *filepaths)


def get_dir_paths(root_dir: str, valid_extensions: list[str], recursive: bool = True, starting_num: int = 0) -> Generator[str, None, None]:
    """
    Yields file paths from root_dir with extensions in valid_extensions.
    If starting_num is set, only yields files under subdirectories >= starting_num.
    """
    root_path = Path(root_dir)
    all_paths = root_path.rglob('*') if recursive else root_path.glob('*')

    for p in all_paths:
        if not p.is_file() or p.suffix.lower() not in valid_extensions:
            continue

        parts = p.relative_to(root_path).parts
        if len(parts) == 3:
            num = int(parts[0])
            if num < starting_num:
                continue

        yield str(p)


def is_valid_file(p: Path, valid_extensions: list[str]) -> bool:
    """Note: exts in valid_extensions must include leading '.'"""
    return p.is_file() and p.suffix.lower() in valid_extensions


def get_valid_extensions(valid_extensions: str) -> list[str]:
    """Returns extensions with a leading '.'"""
    supported_extensions = {'.png', '.jpg', '.jpeg', '.gif'}
    valid_extensions = [f'.{e.strip()}' for e in valid_extensions.split(',')]
    for e in valid_extensions:
        if e not in supported_extensions:
            raise ValueError(supported_extensions, e)
    return valid_extensions


def printr(msg):
    print(f'\r{msg}', end='', flush=True)


def clamp(val, default, min_, max_):
    if not val:
        return default
    if isinstance(val, list):
        return [max(min(v, max_), min_) for v in val]
    return max(min(val, max_), min_)
