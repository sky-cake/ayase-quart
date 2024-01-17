# Ayase Quart


## About

Ayase Quart is a simple, read-only frontend for 4chan archives using the asagi schema. Please see a preview [here](preview/README.md).

This project is a descendent of [Ayase](https://github.com/bibanon/ayase). I chose to port Ayase from FastAPI over to Quart for the following reasons.

- I am more familiar with Flask environments, and Quart is practically just Flask with `async` and `await`.
- Quart has convenient [extensions](http://pgjones.gitlab.io/quart/how_to_guides/quart_extensions.html#quart-extensions).
- It's been stated by numerous sources that the FastAPI developer is not supportive and does not like to accept PRs.
  - [GitHub](https://github.com/tiangolo/fastapi/pulls)
  - [Reddit](https://www.reddit.com/r/Python/comments/xk6ppx/comment/ipd8c62/?utm_source=share&utm_medium=web2x&context=3)


## Set Up

Assuming you have a data source set up, you can

0. Create a file called `secret.txt` in `/src`. Populate it with random text, e.g. `tr -dc A-Za-z0-9 </dev/urandom | head -c 64 > secret.txt`
1. Create a file called `./src/configs.py` using `./rename_to_configs.py`
    - If you do not have a data source to point to, set up [neofuuka](https://github.com/bibanon/neofuuka-scraper) or [Hayden](https://github.com/bbepis/Hayden) with MySQL. See below for their details.
2. Create SSL certificates (see below) and put them in `./src`. They should be called `cert.pem` and `key.pem`.
3. Create a virtualenv and install dependencies,
	- `python3 -m venv venv`
	- `source venv/bin/activate`
	- `python3 -m pip install -r requirements.txt`
	- `sudo apt-get install python3-dev default-libmysqlclient-dev build-essential`
4. `python3 main.py`
5. Visit `https://127.0.0.1:9001` or `https://<IP_ADDRESS>:9001`, depending on whether you're using SSL certs.
6. Submit pull requests with fixes and new features.


## Certificates

These are required to send the QUART_AUTH cookie in the server's response. Save them in `./src`.

If you're on Windows, you can use Git Bash to execute the command.

`openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem`


## Notes

- Right now, only the `tomorrow` theme has complete support.
- If you want to modifying CSS in any way, please modify `/static/css/custom.css`.
- A search function is coming soon!

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
