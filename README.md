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


## Donate & Support

If you like Ayase Quart, please consider donating. 

  - BTC: 3NTq5J41seSiCckK9PJc8cpkD1Bp9CNUSA
  - ETH: 0x1bfCADA8C808Eb3AE7964304F69004a1053Fb1da
  - USDC: 0xAd002E0e9A64DE5e0B93BB7509B475309A2e1ac8

You could also help out by,

  - Opening PRs for fixes or new features
  - Auditing the project
  - Notifying the project of any bugs, security vulnerabilities, or performance issues
  - Proposing new features
  - Testing the project, and reporting noteworthy findings


## License

This project uses the GNU Affero General Public License v3.0 (GNU AGPLv3).

Also, it is expected you will not remove or hide any existing links or references to this GitHub repository. For example, the "Powered by Ayase Quart" footer should remain visible on all Ayase Quart instances.


## Basic Set Up

Use Python 3.12.x or 3.13.x.

At least version SQLite 3.35.0 is required if you want to use the moderation tools. AQ was developed against 3.47.0. You can check your installed version with `python -c "import sqlite3; print(sqlite3.sqlite_version)"`.

Assuming you have a data source set up, you can:

1. Copy `./boards.tpl.toml` to `./boards.toml` and edit `./boards.toml` with your desired boards.
1. Copy `./config.tpl.toml` to `./config.toml` and edit `./config.toml` with proper settings.
	- Generate and set the app secret key. It is used for CSRF, API tokens, and other things.
		- Run `python -c "import secrets as s; print(s.token_hex(24))"` to generate a secret.
		- Change the `app.secret` key in `config.toml` from `DEFAULT_CHANGE_ME` to the generated secret.
    - If you do not have a data source to point to, set up one of the following. Ayase Quart provides some notes [below](#archive-set-up) to help set them up.
      - [Ritual (SQLite)](https://github.com/sky-cake/Ritual)
      - [Neofuuka (MySQL)](https://github.com/bibanon/neofuuka-scraper)
      - [Neofuuka Plus Filters (MySQL)](https://github.com/sky-cake/neofuuka-scraper-plus-filters)
      - [Hayden (MySQL)](https://github.com/bbepis/Hayden) with MySQL.
1. (Optional) If not using a reverse proxy to manage ssl certs for public access, create SSL certificates and put them in cwd (`./`). They should be called `cert.pem` and `key.pem`. See [below](https://github.com/sky-cake/ayase-quart?#certificates) for instructions/
1. Create a virtualenv and install dependencies,
   
    ```bash
    python -m venv venv
    source venv/bin/activate
    python -m pip install -r requirements.txt
    sudo apt update
    sudo apt install python3-dev default-libmysqlclient-dev build-essential redis-server
    ```
1. [Optional] Set up redis for moderation bloom filtering.

    ```bash
    # Set line `supervised no` to `supervised systemd`.
    # Configure listening port and whatever else you want.
    sudo nano /etc/redis/redis.conf

    sudo systemctl restart redis
    sudo systemctl status redis
    ```
1. `python update_js_integrity_values.py` will set HTML `<script>` integrity checksums in a file `asset_hashes.json`.
1. `hypercorn -w 2 -b 127.0.0.1:9001 src:app`
1. Visit `http(s)://<IP_ADDRESS>:<PORT>`. The default is [http://127.0.0.1:9001](http://127.0.0.1:9001).
1. [Optional] Set up a full text search (FTS) database for index searching.
   - Choose a search engine and run its docker container with `docker compose up`.
   - Learn about configuring search engines [here](https://github.com/sky-cake/ayase-quart/wiki/03_SE_Quickstart).
   - Ayase Quart aims to provide (at least partial) support following engines. We have compiled some [search engine notes](./index_search/README.md) during testing phase for your discretion.

        | Engine | GitHub | Notes |
        |-------------|--------|-------|
        | [LNX      ](https://docs.lnx.rs/) | [lnx](https://github.com/lnx-search/lnx) | (fully supported, tested) |
        | [Meili    ](https://www.meilisearch.com/docs/learn/getting_started/installation) | [meilisearch](https://github.com/meilisearch/meilisearch) | (partial support, not tested) |
        | [Manticore](https://manual.manticoresearch.com/Starting_the_server/Docker?client=Docker#Docker-compose) | [manticoresearch](https://github.com/manticoresoftware/manticoresearch) | (partial support, not tested) |
        | [TypeSense](https://typesense.org/docs/guide/install-typesense.html) | [typesense](https://github.com/typesense/typesense) | (partial support, not tested) |
        | [QuickWit ](https://quickwit.io/docs/get-started/quickstart) | [quickwit](https://github.com/quickwit-oss/quickwit) | (partial support, not tested) |

    - Remember to check that your config port matches the docker container port.
    - Run `python -m src.search load --reset board1 [board2 [board3 ...]`.

1. [Optional] Submit pull requests with fixes and new features!


## Database Operations

A package called [asagi-tables](https://github.com/fireballz22/asagi-tables) will allow you to do many Asagi schema operations.


## Plugins

Ayase Quart supports,
  
  - Search plugins for sql and fts. See `src/plugins/search/search_example.py` for an example.
  - Endpoint plugins for custom endpoints. See `src/plugins/blueprints/bp_example.py` for an example.

When starting AQ, detected and loaded plugins are logged to stdout likeso,

```bash
Loading search plugin: plugins.search.search_tagger
Loading bp plugin: plugins.blueprints.bp_tagger
```

**Note:**

There is a computer science problem (?) we've run into with our search plugins called "[post-filtering](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/post-filtering/#single-query-scenario)".

Because plugin search is uncoupled from our native search (AQ's sql or fts search), there is no way to do common pagination. Once we get our board_2_nums from the plugin search results, there is another round of filtering to do via native search. This second round makes final page sizes unpredictable - they can be less than or equal to the plugin search result's page size. For example, final page sizes will often be much less for bigger databases, or more complex search terms. To address this, plugin search developers should do the following,
  - If ONLY plugin form fields have been submitted, do regular paging with your plugin.
  - If additional plugin form fields have been submitted, return more than `per_page` results from your plugins. This makes it more likely for the native search to reach the `per_page` figure.

I'm aware of some other methods to address this (ATTACH DATABASE, multiple-query per-page fill-up), but they seem impractical.

## Set Up with Docker

Not currently available. Feel free to help out with this!


## LNX Setup

Only LNX 0.9.0 is supported. 0.10.0 is not a completed version of LNX.

Terminal A

1. In a terminal, go to `~/ayase-quart/index_search/lnx/`
2. Review the configs in the file `~/ayase-quart/index_search/lnx/docker-compose.yml`
3. Spin up LNX container with `sudo docker-compose up`
   - Later, you can run `sudo docker-compose up -d`, but first we need to confirm it's being populated with data

Terminal B

1. If you haven't already, set the index search configs in `config.toml`.
2. Run `python -m src.search load [options] a b c g gif ...`
3. You should see a bunch of loading bars progressing.
4. In Terminal A, you should see LNX spraying a bunch of output. That's good and means it's working

Now go ahead and try searching the index on you AQ instance in your browser.

Terminal A

1. Once the index loader in Terminal B completes, you can `ctrl-c` to stop the LNX docker container, and spin it back up with `sudo docker-compose up -d` to make it run in the background

Here is a script to help you spin up LNX. You can have a cronjob run this on system reboots if you wish.

```bash
#!/usr/bin/env bash
set -euo pipefail

if ! sudo docker ps --format '{{.Image}}' | grep -q '^chillfish8/lnx'; then
    echo "LNX is down"

    # free buffer cache
    free
    sync
    echo 1 > /proc/sys/vm/drop_caches
    free

    cd /path/to/index_search/lnx/ # set your path
    docker compose up -d
    echo "LNX should be up now"
else
    echo "LNX is already up"
fi
```


## Updating AQ

The `main` branch of this repo is considered to be the latest and greatest version of AQ, ready for production.

1. `git pull --ff origin main`
1. `python update_js_integrity_values.py`
1. `sudo systemctl restart _aq && sleep 1 && sudo systemctl status _aq` assuming a systemd service named `_aq.service` exists.
1. Note: it's possible fields in `configs.toml` have been added or removed.

## Certificates

Certificates are required for moderation (any web-based authentication). AQ will not work without them unless `moderation.auth.cookie_secure=false`.

If you're on Windows, you can use Git Bash to execute the command.

`openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem`

Save the two certs in `./`.


## Themes

AQ only serves a single CSS file, `static/css/custom.css`, which implements the tomorrow theme. Other themes are archived in this repository, but we don't support them.


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

`python -m src.cli.reports`
```bash
Usage: python -m src.cli.reports [OPTIONS] COMMAND [ARGS]...

Options:
--help  Show this message and exit.

Commands:
cli-delete-report
cli-edit-report
cli-get-report-count
cli-get-reports
cli-reports-action
```

`python -m src.cli.reports cli-get-report-count`
```bash
Report count: 4
```

`python -m src.cli.reports cli-get-reports --public_access v --created_at_gte "2024-01-01"`
```bash
|   report_parent_id | board_shortname   |      num |   thread_num | public_access   | mod_status   | mod_notes   |   ip_count | submitter_category          | submitter_notes   | link                                                |
|--------------------+-------------------+----------+--------------+-----------------+--------------+-------------+------------+-----------------------------+-------------------+-----------------------------------------------------|
|                  2 | r9k               | 80365251 |     80365251 | v               | c            | wwww!       |          1 | NSFW content on a SFW board | aa                | http://127.0.0.1:9001/r9k/thread/80365251#p80365251 |
|                  3 | r9k               | 80365280 |     80365251 | v               | o            |             |          1 | DCMA                        | aaaaaa            | http://127.0.0.1:9001/r9k/thread/80365251#p80365280 |
```

`python -m src.cli.reports cli-reports-action --help`
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

### Formatting

Do **not** sort imports automatically. Tools will not respect `#noqa`, and will shuffle or delete `quart_flask_patch`.

Lint checking can be performed using ruff:

```sh
python -m pip install ruff
ruff check
```

### Other
JS `<script>` ressources should be served with integrity checksums in production.
```bash
python update_js_integrity_values.py
```
Running the commands above will create/overwrite `asset_hashes.json`, which contains the hashes of all javascript files under `/static/js`. This file will be loaded into the templating system and render script tags like so:
```html
<script type="text/javascript" defer src="/static/js/index.js" integrity="sha384-b9Ktk8DOJhl3DVyrzWsTxgiKty7CS1etyjL6BIRyTvAaW0e1a3m4VSYlsQpjyqlB"></script>
```
When doing multiple edits during development/debugging, disabling integrity checks can be done by deleting or emptying out the `asset_hashes.json` file. This will produce script tags like this instead:
```html
<script type="text/javascript" defer src="/static/js/index.js"></script>
```

## Production

Check [`systemd.conf`](/systemd.conf) for an example systemd config file.


## Troubleshooting

### MySQL

`MySQL: Access denied for user 'myuser'@'localhost' (using password: YES)`

This is a common issue in mysql distro or image deployments which create incomplete or conflicting user profiles. Here is a solution I found for it, see this [stackoverflow answer](https://stackoverflow.com/a/43037227):

```sql
DROP User 'myuser'@'localhost';
DROP User 'myuser'@'%';
CREATE USER 'myuser'@'%' IDENTIFIED BY 'mypassword';
GRANT ALL PRIVILEGES ON * . * TO 'myuser'@'%';
```

Restart MySQL Server, `sudo systemctl restart mysql`. Check the status `sudo systemctl status mysql`.


## Archive Set Up

### Neofuuka

[Neofuuka](https://github.com/bibanon/neofuuka-scraper) is a good choice if you can't compile Hayden, or don't need Hayden's ultra low memory consumption, but note that you need to use this [Neofuuka fork](https://github.com/sky-cake/neofuuka-scraper) if you want to filter threads since it's not supported in the original version. On the other hand, Hayden supports filtering threads out-of-the-box.

To expedite schema creation, [/db_scripts/init_database.py](/db_scripts/init_database.py)` will create the database specified in `configs.py` with all the necessary tables, triggers, and indexes. Again, Hayden does this out-of-the-box.

### Hayden

Setting up the [Hayden Scraper](https://github.com/bbepis/Hayden) on a Linux Server:

1. Build Hayden on Windows by double clicking `Hayden-master/build.cmd`. This will create a `build-output` folder with zipped builds.
2. Place the linux build on your server.
3. Run `sudo ./Hayden` to check if it's working. You may need to install the .NET 8.0 runtime with `sudo apt install -y dotnet-runtime-8.0` (ubuntu 24.04)
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
