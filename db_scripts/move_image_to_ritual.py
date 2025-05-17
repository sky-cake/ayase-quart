import sqlite3
import sys

db1_path = '/home/yy/Desktop/image.db'
db2_path = '/home/yy/Desktop/ritual_april_16_2025.db'

def get_table_names(conn):
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {row[0] for row in cursor.fetchall()}

def get_index_names(conn):
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
    return {row[0] for row in cursor.fetchall()}

def table_schema(conn, table_name):
    cursor = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    row = cursor.fetchone()
    return row[0] if row else None

def index_schema(conn, index_name):
    cursor = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    row = cursor.fetchone()
    return row[0] if row else None

def copy_table_data(src_conn, dest_conn, table_name):
    rows = src_conn.execute(f"SELECT * FROM {table_name}").fetchall()
    if rows:
        placeholders = ",".join(["?"] * len(rows[0]))
        dest_conn.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)

def main():
    with sqlite3.connect(db1_path) as db1, sqlite3.connect(db2_path) as db2:
        db1_tables = get_table_names(db1)
        db2_tables = get_table_names(db2)

        db1_indexes = get_index_names(db1)
        db2_indexes = get_index_names(db2)

        # Check for collisions
        table_collisions = db1_tables & db2_tables
        index_collisions = db1_indexes & db2_indexes

        if table_collisions or index_collisions:
            print("Collision(s) detected. Aborting.")
            if table_collisions:
                print("Table collisions:", table_collisions)
            if index_collisions:
                print("Index collisions:", index_collisions)
            sys.exit(1)


        assert set(db1_tables) == set(['image', 'tag', 'tag_type', 'image_tag'])

        # No collisions, proceed with copy
        for table in db1_tables:
            schema = table_schema(db1, table)
            print(f"Creating table {table}...")
            db2.execute(schema)

        db2.commit()

        for table in db1_tables:
            print(f"Copying data for table {table}...")
            copy_table_data(db1, db2, table)

        for index in db1_indexes:
            schema = index_schema(db1, index)
            if schema:
                print(f"Creating index {index}...")
                db2.execute(schema)

        db2.commit()
        print("All tables and indexes copied successfully.")

if __name__ == "__main__":
    main()
