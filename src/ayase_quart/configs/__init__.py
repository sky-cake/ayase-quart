from .conf_loader import load_config_file
from .structs import (
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

REPO_PKG = 'ayase_quart'

_conf = load_config_file()

app_conf = AppConfig.from_dict(_conf.get('app', {}))
site_conf = SiteConfig.from_dict(_conf.get('site', {}))
archive_conf = ArchiveConfig.from_dict(_conf.get('archive', {}))
db_conf = DbConfig.from_dict(_conf.get('db', {}))
index_search_conf = IndexSearchConfig.from_dict(_conf.get('index_search', {}))
vanilla_search_conf = VanillaSearchConfig.from_dict(_conf.get('vanilla_search', {}))
redis_conf = RedisConfig.from_dict(_conf.get('redis', {}))
media_conf = MediaConfig.from_dict(_conf.get('media', {}))
mod_conf = ModerationConfig.from_dict(_conf.get('moderation', {}))
stats_conf = StatsConfig.from_dict(_conf.get('stats', {}))
search_plugins_conf = SearchPluginsConfig.from_dict(_conf.get('search_plugins', {}))
