# Ayase Quart

## About

Ayase Quart is a simple, read-only frontend for 4chan archives using the asagi schema. Please see a preview [here](preview/README.md).

This project is a descendent of [Ayase](https://github.com/bibanon/ayase). I chose to port Ayase from FastAPI over to Quart for the following reasons.

- I am more familiar with Flask environments, and Quart is practically just Flask with `async` and `await`.
- Quart has convenient [extensions](http://pgjones.gitlab.io/quart/how_to_guides/quart_extensions.html#quart-extensions).
- It's been stated by numerous sources that the FastAPI developer is not supportive and does not like to accept PRs.
  - [GitHub](https://github.com/tiangolo/fastapi/pulls)
  - [Reddit](https://www.reddit.com/r/Python/comments/xk6ppx/comment/ipd8c62/?utm_source=share&utm_medium=web2x&context=3)

It supports MySQL and SQLite databases.

## Set Up

Please use Python 3.11 or 3.12.

Assuming you have a data source set up, you can:

1. Create a file called `secret.txt` in `/src`. Populate it with random text, e.g. `tr -dc A-Za-z0-9 </dev/urandom | head -c 64 > secret.txt`
2. Create a file called `./src/configs.py` using `./src/rename_to_configs.py`
    - If you do not have a data source to point to, set up [Ritual (SQLite)](https://github.com/sky-cake/Ritual), [Neofuuka (MySQL)](https://github.com/bibanon/neofuuka-scraper), [Neofuuka Plus Filters (MySQL)](https://github.com/sky-cake/neofuuka-scraper-plus-filters) or [Hayden (MySQL)](https://github.com/bbepis/Hayden) with MySQL. Ayase Quart provides some notes below to help set them up.
3. Create SSL certificates (see below) and put them in `./src`. They should be called `cert.pem` and `key.pem`.
4. Create a virtualenv and install dependencies,
    - `python3.12 -m venv venv`
    - `source venv/bin/activate`
    - `python3.12 -m pip install -r requirements.txt`
    - `sudo apt-get install python3-dev default-libmysqlclient-dev build-essential`
5. `python3.12 main.py`
6. Visit `https://127.0.0.1:9001` or `https://<IP_ADDRESS>:9001`, depending on whether you're using SSL certs.
7. (Optional) Set up a full text search (FTS) database for index searching.
   - Choose a search engine and run its docker container with `docker compose up`. Ayase Quart supports the following engines which are ordered from most recommended to least recommended. If you need help deciding, consult our [search engine notes](./index_search/README.md).
     - Meili [[Docs](https://www.meilisearch.com/docs/learn/getting_started/installation) | [GitHub](https://github.com/meilisearch/meilisearch)]
     - Manticore [[Docs](https://manual.manticoresearch.com/Starting_the_server/Docker?client=Docker#Docker-compose) | [GitHub](https://github.com/manticoresoftware/manticoresearch)]
     - MySQL 8.x [[Docs](https://dev.mysql.com/doc/refman/8.4/en/fulltext-search.html) | [GitHub](https://github.com/mysql/mysql-server)]
     - LNX [[Docs](https://docs.lnx.rs/) | [GitHub](https://github.com/lnx-search/lnx)]
     - TypeSense [[Docs](https://typesense.org/docs/guide/install-typesense.html) | [GitHub](https://github.com/typesense/typesense)]
    - Remember to check that your config port matches the docker container port.
    - Go to [Index Search -> Config](http://127.0.0.1:9001/index_search_config) and follow the instructions.
      - Initialize, run.
      - Choose boards, populate, run.
      - Wipe data, if desired, run.
8. (Optional) Submit pull requests with fixes and new features.


## Certificates

These are required to send the QUART_AUTH cookie in the server's response. Save them in `./src`.

If you're on Windows, you can use Git Bash to execute the command.

`openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem`


## Themes

- Right now, only the `tomorrow` theme has complete support.
- If you want to modifying CSS in any way, please modify `/static/css/custom.css`.


## Development

If you want to take debug/dev mode to the next level, you can run the following command which will keep spawning the app, even after errors are raised.

`while true; do hypercorn -w 1 --reload -b 127.0.0.1:9001 'main:app'; done`

## Production

Here is what a systemctl service unit could look like for Ayase Quart.

`sudo nano /etc/systemd/system/ayase_quart.service`

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
