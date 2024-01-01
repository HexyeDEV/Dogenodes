import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def create_db():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        database=os.getenv('DB_NAME')
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
        is_relay INTEGER DEFAULT 0,
        bytes_sent_per_msg TEXT);""")
    c.execute("""CREATE TABLE IF NOT EXISTS peer_history (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        peer_id INTEGER,
        online INTEGER,
        timestamp INTEGER,
        FOREIGN KEY (peer_id) REFERENCES peers(id)
    ) ENGINE=InnoDB;""")
    c.execute("""CREATE TABLE IF NOT EXISTS versions_history
        (id INTEGER PRIMARY KEY AUTO_INCREMENT,
        version TEXT,
        sub_version TEXT,
        timestamp INTEGER);""")
    conn.commit()
    conn.close()