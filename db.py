import mysql.connector

def create_db():
    conn = mysql.connector.connect(
        host='localhost',
        user='yourusername',
        password='yourpassword',
        database='yourdatabase'
    )
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS peers
        (id INT AUTO_INCREMENT PRIMARY KEY,
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
        FOREIGN KEY (peer_id) REFERENCES peers(id)) ENGINE=InnoDB;""")
    c.execute("""CREATE TABLE IF NOT EXISTS versions_history
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT,
        sub_version TEXT,
        timestamp INTEGER);""")
    conn.commit()
    conn.close()