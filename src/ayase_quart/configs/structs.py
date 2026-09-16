from abc import ABC
from dataclasses import MISSING, asdict, dataclass, field, fields, is_dataclass
from os import makedirs, path as osp
from types import UnionType
from typing import Self, Union, get_args, get_origin

from ..enums import DbType, IndexSearchType, MediaFP
from ..utils import split_csv, strip_slashes


class BaseConfig(ABC):
    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(**_configured_dict(cls, d))

    def as_dict(self) -> dict:
        return asdict(self)


def _type_matches(annotation, value) -> bool:
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return any(_type_matches(arg, value) for arg in get_args(annotation))
    if origin is not None:
        return True  # list/tuple/dict/... values are transformed downstream, not strictly checked
    if annotation is type(None):
        return value is None
    if annotation is str:
        return isinstance(value, str)
    if annotation is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if annotation is float:
        return isinstance(value, float)
    if annotation is bool:
        return isinstance(value, bool)
    return True  # enums, nested config classes, etc. are converted in __post_init__


def _fmt_type(annotation) -> str:
    if annotation is type(None):
        return 'None'
    
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return ' | '.join(_fmt_type(arg) for arg in get_args(annotation))
    
    if annotation in (str, int, float, bool):
        return annotation.__name__

    return getattr(annotation, '__name__', str(annotation))


def _raise_type_error(cls, f, value) -> None:
    raise TypeError(f"{cls.__name__} config key '{f.name}' has type {type(value).__name__}, but {f.name}: {_fmt_type(f.type)} was declared")


def _coerce_value(cls, f, value):
    if f.type is int and not isinstance(value, bool):
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                pass
        elif isinstance(value, float) and value.is_integer():
            return int(value)

    if _type_matches(f.type, value):
        return value

    _raise_type_error(cls, f, value)


def _configured_dict(cls, d: dict) -> dict:
    valid = {f.name for f in fields(cls)}
    fields_by_name = {f.name: f for f in fields(cls)}

    for key in d:
        if key not in valid:
            print(f"{cls.__name__} unknown config key '{key}', ignoring")

    for f in fields(cls):
        if f.name in d:
            continue

        if is_dataclass(f.default):
            continue

        if f.default is not MISSING:
            default_repr = repr(f.default)
        elif f.default_factory is not MISSING:
            default_repr = repr(f.default_factory())
        else:
            continue

        print(f"{cls.__name__} missing config key '{f.name}', using default {default_repr}")

    return {
        key: _coerce_value(cls, fields_by_name[key], value)
        for key, value in d.items()
        if key in valid
    }


def _set(self, name: str, value) -> None:
    object.__setattr__(self, name, value)


def _or_default(self, name: str) -> None:
    default = next(f.default for f in fields(self) if f.name == name)
    if default is not MISSING:
        _set(self, name, getattr(self, name) or default)


@dataclass(frozen=True, slots=True)
class AppConfig(BaseConfig):
    testing: bool = False
    secret: str = 'DEFAULT_CHANGE_ME'
    validate_boards_db: bool = True
    autoreload: bool = False
    api: bool = False
    url: str = ''
    port: int = 9001
    ssl_key: str | None = None
    ssl_cert: str | None = None
    proxy_trusted_hops: int = 0
    rate_limiter: bool = True
    allow_robots: bool = False
    login_endpoint: str = '/login'
    use_asagi_side_tables: bool = False

    def __post_init__(self):
        _set(self, 'login_endpoint', f"/{strip_slashes(self.login_endpoint, both=True)}" if self.login_endpoint else '/login')
        _or_default(self, 'ssl_key')
        _or_default(self, 'ssl_cert')
        _or_default(self, 'port')

        if self.secret == 'DEFAULT_CHANGE_ME':
            from secrets import token_hex
            _set(self, 'secret', token_hex(32))
            print('secret not set, generating random secret')


@dataclass(frozen=True, slots=True)
class SiteConfig(BaseConfig):
    name: str = 'Ayase Quart'
    theme: str = 'tomorrow'
    site_email: str = ''
    anonymous_username: str = 'Anonymous'
    custom_banner: str | None = None

    def __post_init__(self):
        _or_default(self, 'theme')
        _or_default(self, 'anonymous_username')


@dataclass(frozen=True, slots=True)
class ArchiveConfig(BaseConfig):
    canonical_name: str
    canonical_host: str
    comments_preescaped: bool = False
    thread_path: str = '/thread/{thread}'
    post_path: str = '#p{num}'
    catalog_path: str = '/catalog'
    cross_thread_previews: bool = False

    def __post_init__(self):
        _or_default(self, 'thread_path')
        _or_default(self, 'post_path')
        _or_default(self, 'catalog_path')


@dataclass(frozen=True, slots=True)
class StatsConfig(BaseConfig):
    enabled: bool = False
    redis: bool = False
    redis_db: int = 2

    def __post_init__(self):
        _or_default(self, 'redis_db')


@dataclass(frozen=True, slots=True)
class MysqlConfig(BaseConfig):
    host: str = ''
    unix_socket: str | None = None
    port: int = 3306
    db: str = ''
    user: str = ''
    password: str = ''
    minsize: int = 1
    maxsize: int = 50
    autocommit: bool = True


@dataclass(frozen=True, slots=True)
class SqliteConfig(BaseConfig):
    database: str = ''


@dataclass(frozen=True, slots=True)
class PostgresqlConfig(BaseConfig):
    host: str = ''
    port: int = 5432
    user: str = ''
    password: str = ''
    database: str = ''
    min_size: int = 1
    max_size: int = 50


@dataclass(frozen=True, slots=True)
class DbConfig(BaseConfig):
    db_type: DbType = DbType.mysql
    echo: bool = False
    mysql: MysqlConfig = MysqlConfig()
    sqlite: SqliteConfig = SqliteConfig()
    postgresql: PostgresqlConfig = PostgresqlConfig()

    def __post_init__(self):
        if not isinstance(self.db_type, DbType):
            _set(self, 'db_type', DbType[self.db_type])

        if isinstance(self.mysql, dict):
            _set(self, 'mysql', MysqlConfig.from_dict(self.mysql))

        if isinstance(self.sqlite, dict):
            _set(self, 'sqlite', SqliteConfig.from_dict(self.sqlite))

        if isinstance(self.postgresql, dict):
            _set(self, 'postgresql', PostgresqlConfig.from_dict(self.postgresql))


@dataclass(frozen=True, slots=True)
class RedisConfig(BaseConfig):
    host: str = '127.0.0.1'
    port: int = 6379
    max_connections: int = 1000
    password: str | None = None
    ssl: bool = False

    def __post_init__(self):
        _or_default(self, 'host')
        _or_default(self, 'port')
        _or_default(self, 'max_connections')
        _or_default(self, 'password')


@dataclass(frozen=True, slots=True)
class MediaConfig(BaseConfig):
    media_fp: MediaFP = MediaFP.asagi
    endpoint: str = ''
    image_uri: str = ''
    thumb_uri: str = ''
    serve_outside_static: bool = False
    media_root_path: str = ''
    valid_extensions: tuple[str, ...] = ('jpg', 'jpeg', 'png', 'gif', 'webm', 'mp4')
    boards_with_image: list[str] = field(default_factory=list)
    boards_with_thumb: list[str] = field(default_factory=list)
    use_nginx_sendfile: bool = False
    nginx_x_accel_redirect_path: str | None = None

    def __post_init__(self):
        if not isinstance(self.media_fp, MediaFP):
            _set(self, 'media_fp', MediaFP[self.media_fp])

        _set(self, 'image_uri', strip_slashes(self.image_uri) if self.image_uri else '')
        _set(self, 'thumb_uri', strip_slashes(self.thumb_uri) if self.thumb_uri else '')
        _set(self, 'boards_with_image', split_csv(self.boards_with_image) if isinstance(self.boards_with_image, str) else (self.boards_with_image or []))
        _set(self, 'boards_with_thumb', split_csv(self.boards_with_thumb) if isinstance(self.boards_with_thumb, str) else (self.boards_with_thumb or []))
        _set(self, 'valid_extensions', tuple(self.valid_extensions or ('jpg', 'jpeg', 'png', 'gif', 'webm', 'mp4')))

        if self.use_nginx_sendfile:
            path = f"/{strip_slashes(self.nginx_x_accel_redirect_path, both=True)}" if self.nginx_x_accel_redirect_path else None

            if not path:
                raise ValueError(path)
            _set(self, 'nginx_x_accel_redirect_path', path)

        else:
            _set(self, 'nginx_x_accel_redirect_path', None)

        if self.serve_outside_static:
            if not all(self.valid_extensions):
                raise ValueError(self.valid_extensions)

            endpoint = strip_slashes(self.endpoint, both=True) if self.endpoint else ''
            _set(self, 'endpoint', endpoint)
            if not endpoint:
                raise ValueError('The set media endpoint is falsey or root (/). Set it to something else.')
        else:
            _set(self, 'endpoint', self.endpoint or '/srv/media')

        if not self.media_root_path:
            print(f'Archived media will not be served because media_root_path={self.media_root_path!r}')
        elif not osp.isdir(self.media_root_path):
            raise ValueError(self.media_root_path)


@dataclass(frozen=True, slots=True)
class VanillaSearchConfig(BaseConfig):
    enabled: bool = False
    highlight: bool = False
    hits_per_page: int = 50
    max_hits: int = 1_000
    multi_board_search: bool = False

    def __post_init__(self):
        _or_default(self, 'hits_per_page')
        _or_default(self, 'max_hits')


@dataclass(frozen=True, slots=True)
class LnxConfig(BaseConfig):
    max_concurrency: int = 4
    reader_threads: int = 4
    writer_threads: int = 4
    writer_buffer: int = 268_435_456

    def __post_init__(self):
        _or_default(self, 'max_concurrency')
        _or_default(self, 'reader_threads')
        _or_default(self, 'writer_threads')
        _or_default(self, 'writer_buffer')


@dataclass(frozen=True, slots=True)
class IndexSearchConfig(BaseConfig):
    enabled: bool = False
    highlight: bool = False
    hits_per_page: int = 50
    max_hits: int = 1_000
    provider: IndexSearchType = IndexSearchType.lnx
    host: str = 'http://localhost:8000'
    headers: dict[str, str] | None = None
    version: str | None = None
    multi_board_search: bool = True
    lnx: LnxConfig = LnxConfig()

    def __post_init__(self):
        if not isinstance(self.provider, IndexSearchType):
            _set(self, 'provider', IndexSearchType[self.provider])

        _or_default(self, 'hits_per_page')
        _or_default(self, 'max_hits')
        _or_default(self, 'host')

        if isinstance(self.lnx, dict):
            _set(self, 'lnx', LnxConfig.from_dict(self.lnx))


@dataclass(frozen=True, slots=True)
class ModerationSqliteConfig(BaseConfig):
    database: str = ''


@dataclass(frozen=True, slots=True)
class AuthConfig(BaseConfig):
    cookie_samesite: str = 'Strict'
    cookie_secure: bool = False
    cookie_http_only: bool = True
    cookie_name: str = 'aq'
    cookie_salt: str = ''
    bearer_salt: str = ''
    cookie_duration: int = 604_800
    bearer_duration: int = 604_800

    def __post_init__(self):
        _or_default(self, 'cookie_samesite')
        _or_default(self, 'cookie_name')
        _or_default(self, 'cookie_duration')
        _or_default(self, 'bearer_duration')


@dataclass(frozen=True, slots=True)
class ModerationConfig(BaseConfig):
    enabled: bool = False
    api: bool = False
    admin_user: str = 'admin'
    admin_password: str = 'admin'
    hide_post_if_reported: bool = False
    n_reports_then_hide: int = 0
    hide_upstream_deleted_posts: bool = False
    remove_replies_to_hidden_op: bool = False
    filter_cache_type: str = 'sqlite'
    regex_filter: str = ''
    path_to_regex_so: str = ''
    hidden_images_path: str = ''
    sqlite: ModerationSqliteConfig = ModerationSqliteConfig()
    auth: AuthConfig = AuthConfig()

    def __post_init__(self):
        _or_default(self, 'admin_user')
        _or_default(self, 'admin_password')
        _or_default(self, 'filter_cache_type')

        if isinstance(self.sqlite, dict):
            _set(self, 'sqlite', ModerationSqliteConfig.from_dict(self.sqlite))

        if isinstance(self.auth, dict):
            _set(self, 'auth', AuthConfig.from_dict(self.auth))

        if self.hidden_images_path:
            makedirs(self.hidden_images_path, exist_ok=True)
            if not osp.isdir(self.hidden_images_path):
                raise ValueError(self.hidden_images_path)

        if self.enabled and self.sqlite.database:
            db_directory = osp.dirname(self.sqlite.database)
            if not osp.isdir(db_directory):
                raise ValueError(
                    f"The moderation database directory does not exist: {db_directory}."
                    f"You set [moderation][sqlite][database] = {self.sqlite.database}"
                )


@dataclass(frozen=True, slots=True)
class SearchPluginsConfig(BaseConfig):
    enabled: bool = False
