import sqlite3

# This should trigger journal recovery
conn = sqlite3.connect("/home/yy/Documents/ritual_april_16_2025.db")
conn.execute("PRAGMA journal_mode = DELETE;")  # Default journal mode
conn.commit()
conn.close()
