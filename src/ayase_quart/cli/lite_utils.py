# because cli.utils is TOO HEAVY! TODO: remove moderation import from cli.utils

def get_confirm(message: str) -> bool:
    resp = input(f'{message} (y/n): ')
    return resp.strip().lower() == 'y'
