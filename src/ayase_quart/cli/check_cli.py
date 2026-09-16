import sys

CONFIG_SECTIONS = [
    ('app', 'app_conf'),
    ('site', 'site_conf'),
    ('archive', 'archive_conf'),
    ('db', 'db_conf'),
    ('index_search', 'index_search_conf'),
    ('vanilla_search', 'vanilla_search_conf'),
    ('redis', 'redis_conf'),
    ('media', 'media_conf'),
    ('moderation', 'mod_conf'),
    ('stats', 'stats_conf'),
    ('search_plugins', 'search_plugins_conf'),
]


def check_cli(args) -> None:
    try:
        from ..configs import (
            archive_conf,
            app_conf,
            db_conf,
            index_search_conf,
            media_conf,
            mod_conf,
            redis_conf,
            search_plugins_conf,
            site_conf,
            stats_conf,
            vanilla_search_conf,
        )
    except Exception as e:
        print(f'config.toml invalid: {e}', file=sys.stderr)
        raise SystemExit(1)

    configs = {
        'app_conf': app_conf,
        'site_conf': site_conf,
        'archive_conf': archive_conf,
        'db_conf': db_conf,
        'index_search_conf': index_search_conf,
        'vanilla_search_conf': vanilla_search_conf,
        'redis_conf': redis_conf,
        'media_conf': media_conf,
        'mod_conf': mod_conf,
        'stats_conf': stats_conf,
        'search_plugins_conf': search_plugins_conf,
    }

    for section, conf_name in CONFIG_SECTIONS:
        conf = configs[conf_name]
        conf.as_dict()
        print(f'{section}: OK')

    print('config.toml valid')