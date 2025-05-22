from .connection import get_connection


def create_tags_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        epc TEXT NOT NULL,
        antenna INTEGER,
        channel INTEGER,
        seen_count INTEGER,
        last_seen TEXT
    )
    """)

    conn.commit()
    conn.close()
