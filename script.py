import requests, json
import mysql.connector
import time
from db import create_db
import os
from dotenv import load_dotenv

load_dotenv()

create_db()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASS'),
    database=os.getenv('DB_NAME')
)


RELAY_NODES = [
    ("ip:post", "username", "password", "actual_port"),
]

def get_peers():
    peers = []
    for node in RELAY_NODES:
        url = f"http://{node[1]}:{node[2]}@{node[0]}"
        data = {
            "method": "getpeerinfo",
            "params": [],
        }
        data = json.dumps(data)
        r = requests.post(url, data=data)
        peers += r.json()['result']
    return peers
    
def is_relay_online(relay):
    try:
        url = f"http://{relay[1]}:{relay[2]}@{relay[0]}"
        data = {
            "method": "getpeerinfo",
            "params": [],
        }
        data = json.dumps(data)
        r = requests.post(url, data=data)
        r.json()
        return True
    except:
        return False
    
def is_valid(peer):
    if peer["banscore"] > 0:
        return False
    if peer["synced_headers"] < peer["synced_blocks"]:
        return False
    try:
        peer["version"] = int(peer["version"])
    except:
        return False
    if peer["version"] < 70000:
        return False
    return True

def get_peer_from_db(ip, port):
    c = conn.cursor()
    c.execute("SELECT * FROM peers WHERE ip=%s AND port=%s", (ip, port))
    return c.fetchone()

def update_peer_history(peer, online, timestamp):
    c = conn.cursor()
    c.execute("INSERT INTO peer_history (peer_id, online, timestamp) VALUES (%s, %s, %s)", (peer[0], online, timestamp))
    conn.commit()

def update_versions_history(version, sub_version, timestamp):
    c = conn.cursor()
    c.execute("INSERT INTO versions_history (version, sub_version, timestamp) VALUES (%s, %s, %s)", (version, sub_version, timestamp))
    conn.commit()

def get_relay_version(relay):
    try:
        url = f"http://{relay[1]}:{relay[2]}@{relay[0]}"
        data = {
            "method": "getnetworkinfo",
            "params": [],
        }
        data = json.dumps(data)
        r = requests.post(url, data=data)
        return r.json()['result']['protocolversion'], r.json()['result']['subversion']
    except:
        return None


def update_all_data():
    peers = get_peers()
    timestamp = int(time.time())
    for peer in peers:
        if not is_valid(peer):
            c = conn.cursor()
            c.execute("UPDATE peers SET online=?, last_check=? WHERE ip=? AND port=?", (0, timestamp, peer["addr"].split(":")[0], peer["addr"].split(":")[1]))
            conn.commit()
            update_peer_history(get_peer_from_db(peer["addr"].split(":")[0], peer["addr"].split(":")[1]), 0, timestamp)
            continue
        version = peer["version"]
        sub_version = peer["subver"]
        if peer["addr"].startswith("["):
            ip = peer["addr"].split("]:")[0] + "]"
            port = peer["addr"].split("]:")[1]
        else:
            ip = peer["addr"].split(":")[0]
            port = peer["addr"].split(":")[1]
        for relay in RELAY_NODES:
            if ip in relay[0]:
                continue
        if get_peer_from_db(ip, port) is None:
            c = conn.cursor()
            c.execute("INSERT INTO peers (ip, port, online, last_seen, session_start, last_check, version, sub_version, is_relay) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (ip, port, 1, timestamp, timestamp, timestamp, version, sub_version, 0))
            conn.commit()
        else:
            c = conn.cursor()
            c.execute("UPDATE peers SET online=%s, last_seen=%s, last_check=%s WHERE ip=%s AND port=%s", (1, timestamp, timestamp, ip, port))
            conn.commit()
        update_peer_history(get_peer_from_db(ip, port), 1, timestamp)
        update_versions_history(version, sub_version, timestamp)
    c = conn.cursor()
    c.execute("SELECT * FROM peers WHERE last_check < ? AND online=? AND is_relay=?", (timestamp - 10, 0, 0))
    peers = c.fetchall()
    for peer in peers:
        update_peer_history(peer, 0, timestamp)
    c = conn.cursor()
    c.execute("SELECT * FROM peers WHERE last_check < ? AND online=? AND is_relay=?", (timestamp - 10, 1, 0))
    peers = c.fetchall()
    for peer in peers:
        c = conn.cursor()
        c.execute("UPDATE peers SET online=?, last_check=?, session_start=?, last_seen=? WHERE ip=? AND port=?", (0, timestamp, 0, timestamp, peer[1], peer[2]))
        conn.commit()
        update_peer_history(peer, 0, timestamp)
    for relay in RELAY_NODES:
        if relay[0].startswith("["):
            ip = relay[0].split("]:")[0] + "]"
            port = relay[0].split("]:")[1]
        else:
            ip = relay[0].split(":")[0]
            port = relay[0].split(":")[1]
        version, sub_version = get_relay_version(relay)
        if is_relay_online(relay):
            actual_port = relay[3]
            if get_peer_from_db(ip, actual_port) is None:
                c = conn.cursor()
                c.execute("INSERT INTO peers (ip, port, online, last_seen, session_start, last_check, version, sub_version, is_relay) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (ip, actual_port, 1, timestamp, timestamp, timestamp, version, sub_version, 1))
                conn.commit()
            else:
                c = conn.cursor()
                c.execute("UPDATE peers SET online=?, last_seen=?, last_check=?, version=?, sub_version=? WHERE ip=? AND port=?", (1, timestamp, timestamp, version, sub_version, ip, actual_port))
                conn.commit()
            update_peer_history(get_peer_from_db(ip, actual_port), 1, timestamp)
            update_versions_history(version, sub_version, timestamp)
        else:
            c = conn.cursor()
            c.execute("UPDATE peers SET online=?, last_check=?, session_start=? WHERE ip=? AND port=?", (0, timestamp, 0, ip, port))
            conn.commit()
            update_peer_history(get_peer_from_db(ip, port), 0, timestamp)

if __name__ == "__main__":
    try:
        while True:
            update_all_data()
            time.sleep(30)
    except KeyboardInterrupt:
        pass
