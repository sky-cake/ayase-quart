# Ayase Quart

## About

Ayase Quart (AQ) is an interface for 4chan archives using the asagi schema. It currently offers,

- [Web UI](preview/README.md) that looks and feels like 4chan
- Advanced search options, with optional full text search (FTS) using lnx, meilisearch, and many others.
- A moderation system to hide, and/or delete content

It supports MySQL and SQLite, so it's compatible with [Neofuuka (MySQL)](https://github.com/bibanon/neofuuka-scraper), [Hayden (MySQL)](https://github.com/bbepis/Hayden), and [Ritual (SQLite)](https://github.com/sky-cake/Ritual) archive downloaders.

This project is a descendent of [Ayase](https://github.com/bibanon/ayase).

## Set Up

Please use Python 3.12.

Assuming you have a data source set up, you can:

1. Copy `./src/boards.tpl.toml` to `./src/boards.toml` and edit `./src/boards.toml` with the desired boards
1. Copy `./src/config.tpl.toml` to `./src/config.toml` and edit `./src/config.toml` with proper setting
	- Generate and set the app secret key (CSRF generation and other things)
		- run `python -c "import secrets as s; print(s.token_hex(24))"` to generate a secret
		- change the `app.secret` key in `config.toml` from 'DEFAULT_CHANGE_ME' to the generated secret
    - If you do not have a data source to point to, set up one of the following. Ayase Quart provides some notes below to help set them up.
      - [Ritual (SQLite)](https://github.com/sky-cake/Ritual)
      - [Neofuuka (MySQL)](https://github.com/bibanon/neofuuka-scraper)
      - [Neofuuka Plus Filters (MySQL)](https://github.com/sky-cake/neofuuka-scraper-plus-filters)
      - [Hayden (MySQL)](https://github.com/bbepis/Hayden) with MySQL.
1. (Optional) Create SSL certificates (see below) and put them in `./src`. They should be called `cert.pem` and `key.pem`.
1. Create a virtualenv and install dependencies,
    - `python3.12 -m venv venv`
    - `source venv/bin/activate`
    - `python3.12 -m pip install -r requirements.txt`
    - `sudo apt-get install python3-dev default-libmysqlclient-dev build-essential`
1. `python3.12 main.py`
1. Visit `http(s)://<IP_ADDRESS>:<PORT>`. The default is `http://127.0.0.1:9001`.
1. (Optional) Set up a full text search (FTS) database for index searching.
   - Choose a search engine and run its docker container with `docker compose up`. Learn about configuring search engines at [https://github.com/sky-cake/ayase-quart/wiki/03_SE_Quickstart](https://github.com/sky-cake/ayase-quart/wiki/03_SE_Quickstart).
   - Ayase Quart aims to provide (at least partial) support following engines. We have compiled some [search engine notes](./index_search/README.md) during testing phase for your discretion.
     - LNX [[Docs](https://docs.lnx.rs/) | [GitHub](https://github.com/lnx-search/lnx)]
     - Meili [[Docs](https://www.meilisearch.com/docs/learn/getting_started/installation) | [GitHub](https://github.com/meilisearch/meilisearch)] (recommended)
     - Manticore [[Docs](https://manual.manticoresearch.com/Starting_the_server/Docker?client=Docker#Docker-compose) | [GitHub](https://github.com/manticoresoftware/manticoresearch)]
     - MySQL 8.x [[Docs](https://dev.mysql.com/doc/refman/8.4/en/fulltext-search.html) | [GitHub](https://github.com/mysql/mysql-server)] (not supported yet)
     - TypeSense [[Docs](https://typesense.org/docs/guide/install-typesense.html) | [GitHub](https://github.com/typesense/typesense)]
     - QuickWit [[Docs](https://quickwit.io/docs/get-started/quickstart) | [GitHub](https://github.com/quickwit-oss/quickwit)]
    - Remember to check that your config port matches the docker container port.
    - Run `python3.12 -m search load --reset board1 [board2 [board3 ...]]`. Go to [Index Search -> Config](http://127.0.0.1:9001/index_search_config) for more instructions.
1. (Optional) Set up redis for rate limiting auth endpoints.

    ```
    sudo apt update
    sudo apt install redis-server
    sudo nano /etc/redis/redis.conf # set line `supervised no` to `supervised systemd`
    sudo systemctl restart redis
    sudo systemctl status redis
    ```

1.  (Optional) Submit pull requests with fixes and new features.


## Set Up (Docker)

Not currently available.

## Certificates

These are required to send the QUART_AUTH cookie in the server's response. Save them in `./src`.

If you're on Windows, you can use Git Bash to execute the command.

`openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem`


## Themes

- Right now, only the `tomorrow` theme has complete support.
- If you want to modify CSS, you can do so in `/static/css/custom.css`.


## Build

Sorting imports

`isort -m 3 ./src`

Lint checking

`flake8 --select F401,F403,F405,E1101,E122,C901,F401,B950 ./src`

## Production

Here is what a systemctl service unit could look like for Ayase Quart.

`sudo nano /etc/systemd/system/aq.service`

```
[Unit]
Description=Ayase Quart - Hypercorn Service
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


## MySQL Troubleshooting

`MySQL: Access denied for user 'myuser'@'localhost' (using password: YES)`

This ALWAYS happens when I'm trying to run privileged transactions. Here is a solution I found for it.

```
DROP User 'myuser'@'localhost';
DROP User 'myuser'@'%';
CREATE USER 'myuser'@'%' IDENTIFIED BY 'mypassword';
GRANT ALL PRIVILEGES ON * . * TO 'myuser'@'%';
```

Restart MySQL Server, `sudo systemctl restart mysql`. Check the status `sudo systemctl status mysql`.


## Neofuuka

[Neofuuka](https://github.com/bibanon/neofuuka-scraper) is a good choice if you can't compile Hayden, or don't need Hayden's ultra low memory consumption, but note that you need to use this [Neofuuka fork](https://github.com/sky-cake/neofuuka-scraper) if you want to filter threads since it's not supported in the original version. On the other hand, Hayden supports filtering threads out-of-the-box.

To expedite schema creation, I have created `./utils/init_database.py` which will create the database specified in `configs.py` with all the necessary tables, triggers, and indexes. Again, Hayden does this out-of-the-box.

## Hayden

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
