# Ayase Quart


## About

This project is a descendent of [Ayase](https://github.com/bibanon/ayase). I chose to port Ayase from FastAPI over to Quart for the following reasons.

- I am more familiar with Flask environments, and Quart is practically just Flask with `async` and `await`.
- Quart has convenient [extensions](http://pgjones.gitlab.io/quart/how_to_guides/quart_extensions.html#quart-extensions),.
  - Quart Auth allowed me quickly add authentication to Ayase Quart.
- It's been stated by numerous sources that the FastAPI developer is not supportive and does not like to accept PRs.
  - [GitHub](https://github.com/tiangolo/fastapi/pulls)
  - [Reddit](https://www.reddit.com/r/Python/comments/xk6ppx/comment/ipd8c62/?utm_source=share&utm_medium=web2x&context=3)


## Set Up

Assuming you have a data source set up, you can

1. Configure `./src/configs.py` using `./rename_to_configs.py`
    - If you do not have a data source to point to, set up [neofuuka](https://github.com/bibanon/neofuuka-scraper) or [Hayden](https://github.com/bbepis/Hayden) with MySQL. See below for their details.
2. Create SSL certificates (see below) and put them in `./src`
3. [optional] Use Docker (`docker compose up`) or virtualenv (`python3.11 virtualenv venv \ pip3.11 install -r requirements.txt`).
4. `python3.11 main.py`
5. Visit `https://127.0.0.1:9003` or `https://<IP_ADDRESS>:9003`



## Certificates

These are required to send the QUART_AUTH cookie in the server's response. Save them in `./src`.

If you're on Windows, you can use Git Bash to execute the command.

`openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem`


## ToDo

Right now, this project is read-only -- the moderator functions do not work.


## Neofuuka

Neofuuka is a great choice if you want to start scraping quickly, but note that it doesn't support regex filtering i.e. it downloads enitre boards. If you want to specify which threads to download, and which threads to definitely not download, use Hayden.

For neofuuka triggers, you may need to replace `;;` with `//` or something else if you get errors.


## Hayden

Setting up the Hayden Scraper on a Linux Server:

1. Build Hayden on Windows by double clicking `Hayden-master/build.cmd`. This will create a `build-output` folder with zipped builds.
2. Place the linux build on your server.
3. Run `sudo ./Hayden` to check if it's working. You may need to install the .NET 6.0 runtime with `sudo apt install -y dotnet-runtime-6.0`
4. Start Hayden with `sudo ./Hayden scrape /path/to/config.json`

Example config.json:

Note: You will need to create the database hayden\_asagi, but Hayden takes care of generating schemas within it.

```json
{
	"source" : {
		"type" : "4chan",
		"boards" : {
			"g": {
				"AnyFilter": "docker",
        "AnyBlacklist": "useless|terrible|hate"
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
