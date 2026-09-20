from os import makedirs, path as osp
from typing import Annotated, Self, get_args

from msgspec import Meta, NODEFAULT, Struct, convert, field, to_builtins
from msgspec.structs import fields as struct_fields
from msgspec.structs import force_setattr

from ..enums import DbType, IndexSearchType, MediaFP
from ..utils import split_csv, strip_slashes


Port = Annotated[int, Meta(ge=1, le=65535)]
NonNegInt = Annotated[int, Meta(ge=0)]
PosInt = Annotated[int, Meta(ge=1)]


def nested_struct(annotation) -> type[Struct] | None:
    for arg in get_args(annotation) or (annotation,):
        if isinstance(arg, type) and issubclass(arg, Struct):
            return arg
    return None


def default_value(info) -> object:
    if info.default_factory is not NODEFAULT and info.default_factory is not None:
        return info.default_factory()
    return info.default


def warn_keys(cls, d: dict) -> None:
    if not isinstance(d, dict):
        return

    infos = struct_fields(cls)
    by_name = {info.name: info for info in infos}

    for info in infos:
        if info.name in d:
            continue

        default = default_value(info)
        if isinstance(default, Struct):
            continue

        if default is NODEFAULT:
            print(f"{cls.__name__} missing required config key '{info.name}'")
            continue

        print(f"{cls.__name__} missing config key '{info.name}', using {default}")

    for name, value in d.items():
        if name not in by_name:
            print(f"{cls.__name__} unknown config key '{name}', ignoring")
            continue

        if isinstance(value, dict) and (nested := nested_struct(by_name[name].type)):
            warn_keys(nested, value)


class BaseConfig(Struct, frozen=True):
    @classmethod
    def from_dict(cls, d: dict) -> Self:
        warn_keys(cls, d)
        return convert(d, cls, strict=True)

    def as_dict(self) -> dict:
        return to_builtins(self)


class AppConfig(BaseConfig):
    testing: bool = False
    secret: str = 'DEFAULT_CHANGE_ME'
    validate_boards_db: bool = True
    autoreload: bool = False
    api: bool = False
    url: str = ''
    port: Port = 9001
    ssl_key: str | None = None
    ssl_cert: str | None = None
    proxy_trusted_hops: NonNegInt = 0
    rate_limiter: bool = True
    allow_robots: bool = False
    login_endpoint: str = '/login'

    def __post_init__(self):
        force_setattr(self, 'login_endpoint', f"/{strip_slashes(self.login_endpoint, both=True)}" if self.login_endpoint else '/login')

        if self.secret == 'DEFAULT_CHANGE_ME':
            from secrets import token_hex
            force_setattr(self, 'secret', token_hex(32))
            print('secret not set, generating random secret')


class SiteConfig(BaseConfig):
    name: str = 'Ayase Quart'
    site_email: str = ''
    anonymous_username: str = 'Anonymous'
    custom_banner: str | None = None


class ArchiveConfig(BaseConfig):
    canonical_name: str
    canonical_host: str
    comments_preescaped: bool = False
    thread_path: str = '/thread/{thread}'
    post_path: str = '#p{num}'
    catalog_path: str = '/catalog'


class StatsConfig(BaseConfig):
    enabled: bool = False
    redis: bool = False
    redis_db: NonNegInt = 2


class MysqlConfig(BaseConfig):
    host: str = ''
    unix_socket: str | None = None
    port: Port = 3306
    db: str = ''
    user: str = ''
    password: str = ''
    minsize: NonNegInt = 1
    maxsize: PosInt = 50
    autocommit: bool = True


class SqliteConfig(BaseConfig):
    database: str = ''


class PostgresqlConfig(BaseConfig):
    host: str = ''
    port: Port = 5432
    user: str = ''
    password: str = ''
    database: str = ''
    min_size: NonNegInt = 1
    max_size: PosInt = 50


class DbConfig(BaseConfig):
    db_type: DbType = DbType.mysql
    echo: bool = False
    mysql: MysqlConfig = MysqlConfig()
    sqlite: SqliteConfig = SqliteConfig()
    postgresql: PostgresqlConfig = PostgresqlConfig()


class RedisConfig(BaseConfig):
    host: str = '127.0.0.1'
    port: Port = 6379
    max_connections: PosInt = 1000
    password: str | None = None
    ssl: bool = False


class MediaConfig(BaseConfig):
    media_fp: MediaFP = MediaFP.asagi
    endpoint: str = ''
    image_uri: str = ''
    thumb_uri: str = ''
    serve_outside_static: bool = False
    media_root_path: str = ''
    valid_extensions: tuple[str, ...] = ('jpg', 'jpeg', 'png', 'gif', 'webm', 'mp4')
    boards_with_image: list[str] | str = field(default_factory=list)
    boards_with_thumb: list[str] | str = field(default_factory=list)
    use_nginx_sendfile: bool = False
    nginx_x_accel_redirect_path: str | None = None

    def __post_init__(self):
        force_setattr(self, 'image_uri', strip_slashes(self.image_uri) if self.image_uri else '')
        force_setattr(self, 'thumb_uri', strip_slashes(self.thumb_uri) if self.thumb_uri else '')
        force_setattr(self, 'boards_with_image', split_csv(self.boards_with_image) if isinstance(self.boards_with_image, str) else (self.boards_with_image or []))
        force_setattr(self, 'boards_with_thumb', split_csv(self.boards_with_thumb) if isinstance(self.boards_with_thumb, str) else (self.boards_with_thumb or []))

        if self.use_nginx_sendfile:
            path = f"/{strip_slashes(self.nginx_x_accel_redirect_path, both=True)}" if self.nginx_x_accel_redirect_path else None

            if not path:
                raise ValueError(path)
            force_setattr(self, 'nginx_x_accel_redirect_path', path)

        else:
            force_setattr(self, 'nginx_x_accel_redirect_path', None)

        if self.serve_outside_static:
            if not all(self.valid_extensions):
                raise ValueError(self.valid_extensions)

            endpoint = strip_slashes(self.endpoint, both=True) if self.endpoint else ''
            force_setattr(self, 'endpoint', endpoint)
            if not endpoint:
                raise ValueError('The set media endpoint is falsey or root (/). Set it to something else.')
        else:
            force_setattr(self, 'endpoint', self.endpoint or '/srv/media')

        if not self.media_root_path:
            print(f'Archived media will not be served because media_root_path={self.media_root_path!r}')
        elif not osp.isdir(self.media_root_path):
            raise ValueError(self.media_root_path)


class VanillaSearchConfig(BaseConfig):
    enabled: bool = False
    highlight: bool = False
    hits_per_page: PosInt = 50
    max_hits: PosInt = 1_000
    multi_board_search: bool = False


class LnxConfig(BaseConfig):
    max_concurrency: PosInt = 4
    reader_threads: PosInt = 4
    writer_threads: PosInt = 4
    writer_buffer: PosInt = 268_435_456


class IndexSearchConfig(BaseConfig):
    enabled: bool = False
    highlight: bool = False
    hits_per_page: PosInt = 50
    max_hits: PosInt = 1_000
    provider: IndexSearchType = IndexSearchType.lnx
    host: str = 'http://localhost:8000'
    headers: dict[str, str] | None = None
    version: str | None = None
    multi_board_search: bool = True
    lnx: LnxConfig = LnxConfig()


class ModerationSqliteConfig(BaseConfig):
    database: str = ''


class AuthConfig(BaseConfig):
    cookie_samesite: str = 'Strict'
    cookie_secure: bool = False
    cookie_http_only: bool = True
    cookie_name: str = 'aq'
    cookie_salt: str = ''
    bearer_salt: str = ''
    cookie_duration: NonNegInt = 604_800
    bearer_duration: NonNegInt = 604_800


class ModerationConfig(BaseConfig):
    enabled: bool = False
    api: bool = False
    admin_user: str = 'admin'
    admin_password: str = 'admin'
    hide_post_if_reported: bool = False
    n_reports_then_hide: NonNegInt = 0
    hide_upstream_deleted_posts: bool = False
    remove_replies_to_hidden_op: bool = False
    filter_cache_type: str = 'sqlite'
    regex_filter: str = ''
    path_to_regex_so: str = ''
    hidden_images_path: str = ''
    sqlite: ModerationSqliteConfig = ModerationSqliteConfig()
    auth: AuthConfig = AuthConfig()

    def __post_init__(self):
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


class SearchPluginsConfig(BaseConfig):
    enabled: bool = False
