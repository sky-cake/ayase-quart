import pytest

from ayase_quart.configs import (
    app_conf,
    archive_conf,
    db_conf,
    index_search_conf,
    media_conf,
    mod_conf,
    redis_conf,
    site_conf,
    stats_conf,
    vanilla_search_conf,
)
from ayase_quart.configs.conf_loader import load_config_file
from ayase_quart.configs.structs import (
    AppConfig,
    ArchiveConfig,
    DbConfig,
    IndexSearchConfig,
    MediaConfig,
    ModerationConfig,
    RedisConfig,
    SearchPluginsConfig,
    SiteConfig,
    StatsConfig,
    VanillaSearchConfig,
)
from ayase_quart.enums import DbType, IndexSearchType, MediaFP


def test_from_dict_matches_loaded_config():
    conf = load_config_file()
    assert app_conf == AppConfig.from_dict(conf.get('app', {}))
    assert site_conf == SiteConfig.from_dict(conf.get('site', {}))
    assert archive_conf == ArchiveConfig.from_dict(conf.get('archive', {}))
    assert db_conf == DbConfig.from_dict(conf.get('db', {}))
    assert index_search_conf == IndexSearchConfig.from_dict(conf.get('index_search', {}))
    assert vanilla_search_conf == VanillaSearchConfig.from_dict(conf.get('vanilla_search', {}))
    assert redis_conf == RedisConfig.from_dict(conf.get('redis', {}))
    assert media_conf == MediaConfig.from_dict(conf.get('media', {}))
    assert mod_conf == ModerationConfig.from_dict(conf.get('moderation', {}))
    assert stats_conf == StatsConfig.from_dict(conf.get('stats', {}))


def test_from_dict_does_not_mutate_source():
    d = {'testing': True, 'login_endpoint': 'loginn'}
    before = dict(d)
    AppConfig.from_dict(d)
    assert d == before


def test_app_config_login_endpoint():
    conf = AppConfig.from_dict({'login_endpoint': 'loginn/sub'})
    assert conf.login_endpoint == '/loginn/sub'
    assert AppConfig.from_dict({}).login_endpoint == '/login'


def test_site_config_defaults_name():
    conf = SiteConfig.from_dict({'name': 'My Site'})
    assert conf.name == 'My Site'
    assert conf.theme == 'tomorrow'


def test_archive_config_defaults():
    conf = ArchiveConfig.from_dict({'canonical_name': '4chan', 'canonical_host': 'https://boards.4chan.org'})
    assert conf.thread_path == '/thread/{thread}'
    assert conf.post_path == '#p{num}'
    assert conf.catalog_path == '/catalog'
    assert conf.cross_thread_previews is False


def test_db_config_converts_type_and_nested():
    conf = DbConfig.from_dict({
        'db_type': 'sqlite',
        'sqlite': {'database': 'x.db'},
    })
    assert conf.db_type == DbType.sqlite
    assert conf.sqlite.as_dict() == {'database': 'x.db'}
    assert conf.mysql.host == ''
    assert conf.echo is False


def test_db_config_mysql_as_dict():
    conf = DbConfig.from_dict({
        'db_type': 'mysql',
        'mysql': {'host': 'h', 'port': 3307, 'db': 'd', 'user': 'u', 'password': 'p'},
    })
    assert conf.db_type == DbType.mysql
    assert conf.mysql.as_dict()['host'] == 'h'


def test_index_search_config_provider_enum():
    conf = IndexSearchConfig.from_dict({'provider': 'lnx'})
    assert conf.provider == IndexSearchType.lnx
    assert conf.lnx.max_concurrency == 4
    assert conf.headers is None


def test_media_config_transforms():
    conf = MediaConfig.from_dict({
        'media_fp': 'sutra',
        'endpoint': 'srv/media/',
        'image_uri': 'http://x/img/',
        'thumb_uri': '',
        'boards_with_image': 'a,o',
        'boards_with_thumb': '',
    })
    assert conf.media_fp == MediaFP.sutra
    assert conf.image_uri == 'http://x/img'
    assert conf.thumb_uri == ''
    assert conf.boards_with_image == ['a', 'o']
    assert conf.boards_with_thumb == []


@pytest.mark.parametrize('cls,extra', [
    (AppConfig, {'unknown_key': 1}),
    (SiteConfig, {'unknown_key': 1}),
    (DbConfig, {'unknown_key': 1}),
    (RedisConfig, {'unknown_key': 1}),
    (MediaConfig, {'unknown_key': 1}),
    (IndexSearchConfig, {'unknown_key': 1}),
    (ModerationConfig, {'unknown_key': 1}),
    (VanillaSearchConfig, {'unknown_key': 1}),
    (StatsConfig, {'unknown_key': 1}),
    (ArchiveConfig, {'canonical_name': 'a', 'canonical_host': 'b', 'unknown_key': 1}),
    (SearchPluginsConfig, {'unknown_key': 1}),
])
def test_unknown_keys_warn(capsys, cls, extra):
    cls.from_dict(extra)
    assert "unknown config key 'unknown_key'" in capsys.readouterr().out


def test_unknown_keys_warn_nested(capsys):
    conf = DbConfig.from_dict({'db_type': 'mysql', 'mysql': {'host': 'h', 'bogus': 1}})
    out = capsys.readouterr().out
    assert "unknown config key 'bogus'" in out
    assert conf.mysql.host == 'h'


def test_db_config_no_nested_default_warnings(capsys):
    DbConfig.from_dict({'db_type': 'sqlite', 'sqlite': {'database': 'x.db'}})
    out = capsys.readouterr().out
    assert "missing config key 'mysql'" not in out
    assert "missing config key 'postgresql'" not in out


def test_wrong_types_raise():
    with pytest.raises(TypeError, match="config key 'port' has type str, but port: int"):
        AppConfig.from_dict({'port': 'not-a-port'})
    with pytest.raises(TypeError, match="config key 'testing' has type str, but testing: bool"):
        AppConfig.from_dict({'testing': 'true'})
    with pytest.raises(TypeError, match="config key 'theme' has type int, but theme: str"):
        SiteConfig.from_dict({'theme': 5})
    with pytest.raises(TypeError, match="config key 'redis_db' has type float, but redis_db: int"):
        StatsConfig.from_dict({'redis_db': 2.5})
    with pytest.raises(TypeError, match="config key 'admin_user' has type int, but admin_user: str"):
        ModerationConfig.from_dict({'admin_user': 1})


def test_stringified_numbers_coerced():
    assert AppConfig.from_dict({'port': '9001'}).port == 9001
    assert AppConfig.from_dict({'port': 9001}).port == 9001
    assert StatsConfig.from_dict({'redis_db': '2'}).redis_db == 2
    assert AppConfig.from_dict({'proxy_trusted_hops': ' 3 '}).proxy_trusted_hops == 3


def test_optional_none_allowed():
    RedisConfig.from_dict({'password': None})
    AppConfig.from_dict({'ssl_key': None})
    SiteConfig.from_dict({'custom_banner': None})


def test_search_plugins_default_disabled():
    assert SearchPluginsConfig.from_dict({}).enabled is False


def test_or_default_coerces_falsy():
    conf = SiteConfig.from_dict({'theme': '', 'anonymous_username': ''})
    assert conf.theme == 'tomorrow'
    assert conf.anonymous_username == 'Anonymous'

    redis = RedisConfig.from_dict({'host': '', 'port': 0, 'password': ''})
    assert redis.host == '127.0.0.1'
    assert redis.port == 6379
    assert redis.password is None

    search = IndexSearchConfig.from_dict({'hits_per_page': 0, 'host': ''})
    assert search.hits_per_page == 50
    assert search.host == 'http://localhost:8000'


def test_or_default_preserves_explicit_values_and_none():
    conf = SiteConfig.from_dict({'theme': 'ocean', 'site_email': '', 'custom_banner': None})
    assert conf.theme == 'ocean'
    assert conf.site_email == ''
    assert conf.custom_banner is None

    redis = RedisConfig.from_dict({'port': 1234, 'password': None, 'ssl': False})
    assert redis.port == 1234
    assert redis.password is None
    assert redis.ssl is False


def test_missing_keys_warn(capsys):
    full = {'name': 'S', 'theme': 'ocean', 'site_email': 'e', 'anonymous_username': 'a', 'custom_banner': 'b'}
    SiteConfig.from_dict(full)
    assert "missing config key" not in capsys.readouterr().out

    SiteConfig.from_dict({'name': 'S', 'theme': 'ocean'})
    out = capsys.readouterr().out
    assert "missing config key 'name'" not in out
    assert "missing config key 'theme'" not in out
    assert "missing config key 'site_email'" in out
    assert "missing config key 'anonymous_username'" in out
    assert "missing config key 'custom_banner'" in out