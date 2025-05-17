# Ayase Quart


## About

Ayase Quart (AQ) is an interface for 4chan/Lainchan archives using the Asagi database schema. It currently offers,

- A web ui that looks and feels like 4chan.
  - See [here](preview/README.md) for images.
- Advanced search options.
  - Search replies where the opening post's comment includes a specific pattern.
  - Full-text-search (FTS) using lnx, meilisearch, and others engines are supported.
  - Gallery mode for search results.
- A moderation system.
  - View reports.
  - Auto-hide reported content.
  - Filter all content based on a regex pattern.
  - Web, API, and CLI support.

AQ supports MySQL and SQLite, so it's compatible with [Neofuuka (MySQL)](https://github.com/bibanon/neofuuka-scraper), [Hayden (MySQL)](https://github.com/bbepis/Hayden), and [Ritual (SQLite)](https://github.com/sky-cake/Ritual) archive downloaders.

This project is a descendent of [Ayase](https://github.com/bibanon/ayase).


## Donate

If you like Ayase Quart, please consider donating. 

  - BTC: 3NTq5J41seSiCckK9PJc8cpkD1Bp9CNUSA
  - ETH: 0x1bfCADA8C808Eb3AE7964304F69004a1053Fb1da
  - USDC: 0xAd002E0e9A64DE5e0B93BB7509B475309A2e1ac8


## License

This project uses the GNU Affero General Public License v3.0 (GNU AGPLv3).

Also, it is expected you will not remove or hide any existing links or references to this GitHub repository. For example, the "Powered by Ayase Quart" footer should remain visible on all Ayase Quart instances.


## Basic Set Up

Python 3.13.x is required.

Assuming you have a data source set up, you can:

1. Copy `./src/boards.tpl.toml` to `./src/boards.toml` and edit `./src/boards.toml` with your desired boards.
1. Copy `./src/config.tpl.toml` to `./src/config.toml` and edit `./src/config.toml` with proper settings.
	- Generate and set the app secret key. It is used for CSRF, API tokens, and other things.
		- Run `python3.13 -c "import secrets as s; print(s.token_hex(24))"` to generate a secret.
		- Change the `app.secret` key in `config.toml` from `DEFAULT_CHANGE_ME` to the generated secret.
    - If you do not have a data source to point to, set up one of the following. Ayase Quart provides some notes below to help set them up.
      - [Ritual (SQLite)](https://github.com/sky-cake/Ritual)
      - [Neofuuka (MySQL)](https://github.com/bibanon/neofuuka-scraper)
      - [Neofuuka Plus Filters (MySQL)](https://github.com/sky-cake/neofuuka-scraper-plus-filters)
      - [Hayden (MySQL)](https://github.com/bbepis/Hayden) with MySQL.
1. (Optional) Create SSL certificates and put them in `./src`. They should be called `cert.pem` and `key.pem`. See [below](https://github.com/sky-cake/ayase-quart?#certificates) for instructions/
1. Create a virtualenv and install dependencies,
   
    ```bash
    python3.13 -m venv venv
    source venv/bin/activate
    python3.13 -m pip install -r requirements.txt
    sudo apt update
    sudo apt install python3-dev default-libmysqlclient-dev build-essential redis-server
    ```
1. Set up redis.

    ```bash
    # Set line `supervised no` to `supervised systemd`.
    # Configure listening port and whatever else you want.
    sudo nano /etc/redis/redis.conf

    sudo systemctl restart redis
    sudo systemctl status redis
    ```
1. `python3.13 main.py`
1. Visit `http(s)://<IP_ADDRESS>:<PORT>`. The default is [http://127.0.0.1:9001](http://127.0.0.1:9001).
1. [Optional] Set up a full text search (FTS) database for index searching.
   - Choose a search engine and run its docker container with `docker compose up`.
   - Learn about configuring search engines [here](https://github.com/sky-cake/ayase-quart/wiki/03_SE_Quickstart).
   - Ayase Quart aims to provide (at least partial) support following engines. We have compiled some [search engine notes](./index_search/README.md) during testing phase for your discretion.

        | Engine | GitHub | Notes |
        |-------------|--------|-------|
        | [LNX      ](https://docs.lnx.rs/) | [lnx](https://github.com/lnx-search/lnx) | (1st recommendation) |
        | [Meili    ](https://www.meilisearch.com/docs/learn/getting_started/installation) | [meilisearch](https://github.com/meilisearch/meilisearch) | (2nd recommendation) |
        | [Manticore](https://manual.manticoresearch.com/Starting_the_server/Docker?client=Docker#Docker-compose) | [manticoresearch](https://github.com/manticoresoftware/manticoresearch) | (supported, not tested) |
        | [TypeSense](https://typesense.org/docs/guide/install-typesense.html) | [typesense](https://github.com/typesense/typesense) | (supported, not tested) |
        | [QuickWit ](https://quickwit.io/docs/get-started/quickstart) | [quickwit](https://github.com/quickwit-oss/quickwit) | (supported, not tested) |
        | [MySQL 8.x](https://dev.mysql.com/doc/refman/8.4/en/fulltext-search.html) | [mysql-server](https://github.com/mysql/mysql-server) | (not supported) |

    - Remember to check that your config port matches the docker container port.
    - Run `python3.13 -m search load --reset board1 [board2 [board3 ...]`.
      - Go to [Index Search -> Config](http://127.0.0.1:9001/index_search_config) for auto-generated instructions.

1. [Optional] Submit pull requests with fixes and new features!


## Set Up with Docker

Not currently available. Feel free to help out with this!


## Certificates

Certificates are required for moderation (any web-based authentication). AQ will not work without them unless `moderation.auth.cookie_secure=true`.

If you're on Windows, you can use Git Bash to execute the command.

`openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem`

Save the two certs in `./src`.


## Themes

- Right now, only the `tomorrow` theme has complete support.
- If you want to modify CSS, you can do so in `/static/css/custom.css`.


## User Manual

- The default URL is [http://127.0.0.1:9001](http://127.0.0.1:9001).
- Documentation for Web and API endpoints can be found at /docs.

The moderation system requires authentication. The default username and password is `admin`.

### Web
- The web ui uses cookie based authentication. In order to log in, you must solve a math captcha.

### API
- The API uses bearer-token based authentication. You must create a header called `Authorization` with the value `bearer: <token>` on each request. A token is first generated by sending a POST request to `http://localhost:9001/api/v1/login`. The expiration of tokens depends on the configuration of AQ.
- An alternative to Postman/Insomnia called [Bruno](https://github.com/usebruno/bruno) can be used to develop against the API. The collection `/dev/bruno_aq.json` can be imported into Bruno.

### CLI
- No authentication is used for this because access to the server is required.
- The CLI is used to manage user-submitted reports.

Here is a test drive of the cli.

`python3.13 ./src/cli/reports.py`
```bash
Usage: python3.13 ./src/cli/reports.py [OPTIONS] COMMAND [ARGS]...

Options:
--help  Show this message and exit.

Commands:
cli-delete-report
cli-edit-report
cli-get-report-count
cli-get-reports
cli-reports-action
```

`python3.13 ./src/cli/reports.py cli-get-report-count`
```bash
Report count: 4
```

`python3.13 ./src/cli/reports.py cli-get-reports --public_access v --created_at_gte "2024-01-01"`
```bash
|   report_parent_id | board_shortname   |      num |   thread_num | public_access   | mod_status   | mod_notes   |   ip_count | submitter_category          | submitter_notes   | link                                                |
|--------------------+-------------------+----------+--------------+-----------------+--------------+-------------+------------+-----------------------------+-------------------+-----------------------------------------------------|
|                  2 | r9k               | 80365251 |     80365251 | v               | c            | wwww!       |          1 | NSFW content on a SFW board | aa                | http://127.0.0.1:9001/r9k/thread/80365251#p80365251 |
|                  3 | r9k               | 80365280 |     80365251 | v               | o            |             |          1 | DCMA                        | aaaaaa            | http://127.0.0.1:9001/r9k/thread/80365251#p80365280 |
```

`python3.13 ./src/cli/reports.py cli-reports-action --help`
```bash
Usage: reports.py cli-reports-action [OPTIONS]

Options:
-id, --report_parent_id INTEGER
                                [required]
-action, --action [report_delete|post_delete|media_delete|media_hide|media_show|post_show|post_hide|report_close|report_open|report_save_notes]
                                [required]
-notes, --mod_notes TEXT
--help                          Show this message and exit.
```


## Contributing

Do **not** sort imports automatically. Tools will not respect `#noqa`, and will shuffle or delete `quart_flask_patch`.

Lint checking can be performed with,

`python3.13 -m pip install ruff`

`ruff check src/ --ignore F401`


## Production

Here is what a systemctl service file could look like for Ayase Quart.

`sudo nano /etc/systemd/system/aq.service`

```
[Unit]
Description=ayase_quart_hypercorn
After=network.target

[Service]
User=USER1
Group=USER1

WorkingDirectory=/path/to/ayase_quart/src
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/hypercorn -w 2 -b 127.0.0.1:9001 'main:app'

Type=simple
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```


## Troubleshooting

### MySQL

`MySQL: Access denied for user 'myuser'@'localhost' (using password: YES)`

This **ALWAYS** happens when I'm trying to run privileged transactions. Here is a solution I found for it.

```
DROP User 'myuser'@'localhost';
DROP User 'myuser'@'%';
CREATE USER 'myuser'@'%' IDENTIFIED BY 'mypassword';
GRANT ALL PRIVILEGES ON * . * TO 'myuser'@'%';
```

Restart MySQL Server, `sudo systemctl restart mysql`. Check the status `sudo systemctl status mysql`.


## Archive Set Up

### Neofuuka

[Neofuuka](https://github.com/bibanon/neofuuka-scraper) is a good choice if you can't compile Hayden, or don't need Hayden's ultra low memory consumption, but note that you need to use this [Neofuuka fork](https://github.com/sky-cake/neofuuka-scraper) if you want to filter threads since it's not supported in the original version. On the other hand, Hayden supports filtering threads out-of-the-box.

To expedite schema creation, I have created `./utils/init_database.py` which will create the database specified in `configs.py` with all the necessary tables, triggers, and indexes. Again, Hayden does this out-of-the-box.

### Hayden

Setting up the [Hayden Scraper](https://github.com/bbepis/Hayden) on a Linux Server:

1. Build Hayden on Windows by double clicking `Hayden-master/build.cmd`. This will create a `build-output` folder with zipped builds.
2. Place the linux build on your server.
3. Run `sudo ./Hayden` to check if it's working. You may need to install the .NET 6.0 runtime with `sudo apt install -y dotnet-runtime-6.0`
4. Start Hayden with `sudo ./Hayden scrape /path/to/config.json`

Example config.json:

Note: You will need to create the database hayden_asagi, but Hayden takes care of generating schemas within it.

```json
{
    "source" : {
        "type" : "4chan",
        "boards" : {
            "g": {
                "AnyFilter": "docker",
                "AnyBlacklist": "sql|javascript|terraform"
            },
        },
        
        "apiDelay" : 5.5,
        "boardScrapeDelay" : 300
    },

    "readArchive": false,
    
    "proxies" : [],
    
    "consumer" : {
        "type" : "Asagi",

        "databaseType": "MySQL",
        "connectionString" : "Server=localhost;Port=3306;Database=hayden_asagi;Uid=USERNAME;Pwd=PASSWORD;",
        
        "downloadLocation" : "/path/to/image/download/directory",
        
        "fullImagesEnabled" : true,
        "thumbnailsEnabled" : true
    }
}
```
