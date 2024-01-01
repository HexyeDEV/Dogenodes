from fastapi import FastAPI, Query
import aiomysql
import uvicorn, time
from dotenv import load_dotenv
import os, json

load_dotenv()

app = FastAPI()

@app.on_event("startup")
async def startup():
    app.db_connection = await aiomysql.create_pool(host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), db=os.getenv("DB_NAME"), autocommit=True)

@app.on_event("shutdown")
async def shutdown():
    app.db_connection.close()
    await app.db_connection.wait_closed()

def jsonify_peer(peer):
    if peer[9] == 1:
        bytes_sent_per_msg = {"No data for relay nodes": 0}
    else:
        bytes_sent_per_msg = json.loads(peer[10])

    return {
        "id": peer[0],
        "ip": peer[1],
        "port": peer[2],
        "online": peer[3],
        "last_seen": peer[4],
        "session_start": peer[5],
        "last_check": peer[6],
        "version": peer[7],
        "sub_version": peer[8],
        "bytes_sent_per_msg": bytes_sent_per_msg,
    }

async def jsonify_peers(peers, pages):
    result = []
    for peer in peers:
        result.append(jsonify_peer(peer))
        result[-1]["uptime"] = await get_uptime(peer[0])
    return result, {"pages": int(pages)}

def jsonify_peer_history(peer_history, pages):
    res = []
    for history in peer_history:
        res.append({
            "id": history[0],
            "peer_id": history[1],
            "online": history[2],
            "timestamp": history[3],
        })
    return res, {"pages": int(pages)}

def jsonify_versions_history(versions_history, pages):
    return {
        "id": versions_history[0],
        "version": versions_history[1],
        "sub_version": versions_history[2],
        "timestamp": versions_history[3],
    }, {"pages": int(pages)}

async def get_uptime(peer_id):
    async with app.db_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM peers WHERE id=%s", (peer_id,))
            session_start = await cursor.fetchone()
            if session_start is None:
                return 0
            session_start = session_start[5]
        return int(time.time()) - session_start

def show_days(seconds):
    return int(seconds / 86400)

@app.get("/peers")
async def get_peers(page: int = Query(0, alias="page")):
    """Get a list of peers. (50 per page)

    Args:
        page (int): The page number."""
    async with app.db_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM peers ORDER BY online DESC, session_start ASC, last_seen DESC LIMIT 50 OFFSET %s", (page * 50,))
            peers = await cursor.fetchall()
            await cursor.execute("SELECT COUNT(*) FROM peers")
            total_pages = await cursor.fetchone()
            total_pages = total_pages[0] / 50
            res = await jsonify_peers(peers, total_pages)
            return res
    
@app.get("/peer/get/{ip}/{port}")
async def get_peer(ip: str, port: int):
    """Get a peer by ip and port.

    Args:
        ip (str): The ip address of the peer.
        port (int): The port of the peer."""
    async with app.db_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM peers WHERE ip=%s AND port=%s", (ip, port))
            return jsonify_peer(await cursor.fetchone())
    
@app.get("/peer/get/{peer_id}")
async def get_peer_by_id(peer_id: int):
    """Get a peer by id.

    Args:
        peer_id (int): The id of the peer."""
    async with app.db_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM peers WHERE id=%s", (peer_id,))
            peer = await cursor.fetchone()
            if peer is None:
                return {"error": "Peer not found."}
            return {
                "peer": jsonify_peer(peer),
                "uptime": await get_uptime(peer_id),
            }
    
@app.get("/peer/{peer_id}/history")
async def get_peer_history(peer_id: int, page: int = Query(0, alias="page")):
    """Get a peer's history. (50 per page)

    Args:
        peer_id (int): The id of the peer.
        page (int): The page number."""
    async with app.db_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM peer_history WHERE peer_id=%s ORDER BY timestamp DESC LIMIT 50 OFFSET %s", (peer_id, page * 50))
            hitsory = await cursor.fetchall()
            await cursor.execute("SELECT COUNT(*) FROM peer_history WHERE peer_id=%s", (peer_id,))
            total_pages = await cursor.fetchone()
            total_pages = total_pages[0] / 50
            return jsonify_peer_history(hitsory, total_pages)
    
@app.get("/peer/{peer_id}/uptime")
async def get_peer_uptime(peer_id: int):
    """Get a peer's uptime
    Eg: 1 day, 2 hours, 3 minutes, 4 seconds

    Args:
        peer_id (int): The id of the peer."""
    days = show_days(await get_uptime(peer_id))
    return f"{days} days, {time.strftime('%H hours, %M minutes, %S seconds', time.gmtime(await get_uptime(peer_id)))}"

@app.get("/versions/history")
async def get_versions_history(page: int = Query(0, alias="page")):
    """Get the versions history. (50 per page)

    Args:
        page (int): The page number."""
    async with app.db_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM versions_history ORDER BY id ASC LIMIT 50 OFFSET %s", (page * 50,))
            versions_history = await cursor.fetchall()
            await cursor.execute("SELECT COUNT(*) FROM versions_history")
            total_pages = await cursor.fetchone()
            total_pages = total_pages[0] / 50
            return jsonify_versions_history(versions_history, total_pages)

@app.get("/nodes/online")
async def get_nodes_online():
    """Get the number of nodes online."""
    async with app.db_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM peers WHERE online=%s", (1,))
            count = await cursor.fetchone()
            return {"count": count[0]}
    
@app.get("/peer/{peer_id}/uptime/percentage/{amount}/{period_unit}")
async def get_peer_uptime_percentage(peer_id: int, amount: int, period_unit: str):
    """Get a peer's uptime percentage.

    Args:
        peer_id (int): The id of the peer.
        amount (int): The amount of the period.
        period_unit (str): The unit of the period. (hour, day, week, month, year)"""
    if period_unit == "hour":
        period = 3600
    elif period_unit == "day":
        period = 86400
    elif period_unit == "week":
        period = 604800
    elif period_unit == "month":
        period = 2629743
    elif period_unit == "year":
        period = 31556926
    else:
        return {"error": "Invalid period unit."}
    async with app.db_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM peer_history WHERE peer_id=%s AND online=1 AND timestamp > %s", (peer_id, int(time.time()) - amount * period))
            count_online = await cursor.fetchone()
            await cursor.execute("SELECT COUNT(*) FROM peer_history WHERE peer_id=%s AND timestamp > %s", (peer_id, int(time.time()) - amount * period))
            count_total = await cursor.fetchone()
            return {"percentage": count_online[0] / count_total[0] * 100}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0")