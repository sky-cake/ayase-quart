## Search Engine Notes

Since we have a native MySQL search page available to use, a dedicated search engine is optional.

For setting up a Search Engine, please consult [https://github.com/sky-cake/ayase-quart/wiki/03_SE_Quickstart](https://github.com/sky-cake/ayase-quart/wiki/03_SE_Quickstart).

### Search Engines

- LNX [[Docs](https://docs.lnx.rs/) | [GitHub](https://github.com/lnx-search/lnx)]
- Meili [[Docs](https://www.meilisearch.com/docs/learn/getting_started/installation) | [GitHub](https://github.com/meilisearch/meilisearch)]
- Manticore [[Docs](https://manual.manticoresearch.com/Starting_the_server/Docker?client=Docker#Docker-compose) | [GitHub](https://github.com/manticoresoftware/manticoresearch)]
- MySQL 8.x [[Docs](https://dev.mysql.com/doc/refman/8.4/en/fulltext-search.html) | [GitHub](https://github.com/mysql/mysql-server)]
- TypeSense [[Docs](https://typesense.org/docs/guide/install-typesense.html) | [GitHub](https://github.com/typesense/typesense)]
- QuickWit [[Docs](https://quickwit.io/docs/get-started/quickstart) | [GitHub](https://github.com/quickwit-oss/quickwit)]


### Notes

- **LNX** (Recommended)
    - **Generation**: 4
    - **Language**: Rust
    - **Pros**:
        - Extremely fast, less than 2ms for 100 results
    - **Cons**:
        - No boolean support
        - No null support
        - Requires locking for writing (only single API writer allowed, what a bad design)
        - Documentation lacking
        - Latest Docker image 0.10.0 doesn't launch
        - Working Docker image 0.9.0 has old version of Tantivy (0.18.0)
        - Has double quote escape issues
        - No multi-server support
    - **Notes**:
        - Uses Tantivy for first stage
        - Markets itself as consistent performance under load vs Meili & Typesense
        - Not exactly ready for prime time
- **Meili**
    - **Generation**: 3
    - **Language**: Rust
    - **Pros**:
        - Very low in RAM usage, leverages disk as much as possible
        - Has built-in UI to debug
    - **Cons**:
        - No infix search
        - Slow ingestion, feels like it's stuck on 1 core at a certain stage
        - Limited by disk speeds (not that important in practice)
        - Single node only which might not be an issue
        - [Only considers the first ten words of any given search query](https://www.meilisearch.com/docs/reference/api/search#query-q)
    - **Notes**:
        - The standard to compare other search engines to
- **TypeSense**
    - **Generation**: 3
    - **Language**: C++
    - **Pros**:
        - Allows caching search results to reduce server load
    - **Cons**:
        - No null support
        - Doesn't have a primary key concept, so if you add the same document multiple times, it just duplicates them in the index.
        - Doesn't appear to allow unlimited results. 100 results works, 10,000 results does not work.
    - **Notes**:
      - More of a letdown compared to Meilisearch
      - Doesn't allow un-authenticated dev mode
- **Manticore**
    - **Generation**: 4
    - **Language**: C++
    - **Pros**:
        - Has a MySQL compatible API in addition to HTTP
        - Provides official clients for various languages
        - Auto data sync from various sources
    - **Cons**:
        - No null support
        - No boolean support
        - Their sql parser crashes on termination semi-colons (;)
    - **Notes**:
        - Based on Sphinx (forked 2018)
        - Next release should support nulls in json
        - Used by craigslist
        - Even though they offer multiple engines, we're forced to go with columnar by default of our dataset size
        - Markets itself as an Elasticsearch killer
