### 2024-06-12

- [feature] configs.CONSTS - `html_linked_target = '_self' # or '_blank' # links to 4chan will always remain '_blank'`
- [feature] media handling - expand and load full media on click
- [security] Dependabot suggestions

### 2024-06-10

- [feature] sqlite3 support - to update run `git fetch origin && git reset --hard origin/master` and add the following to configs.CONSTS
  - db_aiosqlite = False
  - db_path = make_path('/path/to/archive.db')
  - db_aiomysql = True
