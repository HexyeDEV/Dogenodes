import sqlite3

def create_db():
    conn = sqlite3.connect("db.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS peers
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT,
        port INTEGER,
        online INTEGER DEFAULT 0,
        last_seen INTEGER DEFAULT 0,
        session_start INTEGER DEFAULT 0,
        last_check INTEGER DEFAULT 0,
        version TEXT,
        sub_version TEXT,
        is_relay INTEGER DEFAULT 0);""")
    c.execute("""CREATE TABLE IF NOT EXISTS peer_history
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        peer_id INTEGER,
        online INTEGER,
        timestamp INTEGER,
        FOREIGN KEY (peer_id) REFERENCES peers(id));""")
    c.execute("""CREATE TABLE IF NOT EXISTS versions_history
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT,
        sub_version TEXT,
        timestamp INTEGER);""")
    conn.commit()
    conn.close()