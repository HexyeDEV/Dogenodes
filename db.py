import pymysql

def create_db():
    conn = pymysql.connect(host='localhost', user='yourusername', password='yourpassword', database='yourdbname')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS peers
        (id INTEGER PRIMARY KEY AUTO_INCREMENT,
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
        (id INTEGER PRIMARY KEY AUTO_INCREMENT,
        peer_id INTEGER,
        online INTEGER,
        timestamp INTEGER,
        FOREIGN KEY (peer_id) REFERENCES peers(id)) ENGINE=InnoDB;""")
    c.execute("""CREATE TABLE IF NOT EXISTS versions_history
        (id INTEGER PRIMARY KEY AUTO_INCREMENT,
        version TEXT,
        sub_version TEXT,
        timestamp INTEGER) ENGINE=InnoDB;""")
    conn.commit()
    conn.close()