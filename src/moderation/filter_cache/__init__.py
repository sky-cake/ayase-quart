from .base_fc import BaseFilterCache

def get_filter_cache(mod_conf: dict) -> BaseFilterCache:
    if not mod_conf.get('enabled', False):
        from .null_fc import FilterCacheNull
        return FilterCacheNull(mod_conf)

    filter_cache_type = mod_conf['filter_cache_type']
    match filter_cache_type:
        case 'sqlite':
            from .sqlite_fc import FilterCacheSqlite
            return FilterCacheSqlite(mod_conf)
        case 'redis':
            from .redis_fc import FilterCacheRedis
            return FilterCacheRedis(mod_conf)
        case _:
            raise NotImplementedError(f'Unsupported filter cache type: {filter_cache_type}')
