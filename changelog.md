### 2024-06-12

[NEW] configs.CONSTS - `html_linked_target = '_self' # or '_blank' # links to 4chan will always remain '_blank'`
[CHANGE] media handling - Try to load a thumbnail, if it does not exist, try to load the full media. In any case, if a video exists, load it.
[SECURITY] Dependabot suggestions

### 2024-06-10

[NEW] sqlite3 support - to update run `git fetch origin && git reset --hard origin/master` and add the following to configs.CONSTS
    - db_aiosqlite = False
    - db_path = make_path('/path/to/archive.db')
    - db_aiomysql = True
