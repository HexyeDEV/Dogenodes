from fastapi import FastAPI, Query
import aiosqlite
import uvicorn, time

app = FastAPI()

@app.on_event("startup")
async def startup():
    app.db_connection = await aiosqlite.connect("db.db")

@app.on_event("shutdown")
async def shutdown():
    await app.db_connection.close()

def jsonify_peer(peer):
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
    async with app.db_connection.execute("SELECT * FROM peers WHERE id=?", (peer_id,)) as cursor:
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
    async with app.db_connection.execute("SELECT * FROM peers ORDER BY online DESC, last_seen DESC LIMIT 50 OFFSET ?", (page * 50,)) as cursor:
        total_pages = await app.db_connection.execute("SELECT COUNT(*) FROM peers")
        total_pages = await total_pages.fetchone()
        total_pages = total_pages[0] / 50
        res = await jsonify_peers(await cursor.fetchall(), total_pages)
        return res
    
@app.get("/peer/get/{ip}/{port}")
async def get_peer(ip: str, port: int):
    """Get a peer by ip and port.

    Args:
        ip (str): The ip address of the peer.
        port (int): The port of the peer."""
    async with app.db_connection.execute("SELECT * FROM peers WHERE ip=? AND port=?", (ip, port)) as cursor:
        return jsonify_peer(await cursor.fetchone())
    
@app.get("/peer/get/{peer_id}")
async def get_peer_by_id(peer_id: int):
    """Get a peer by id.

    Args:
        peer_id (int): The id of the peer."""
    async with app.db_connection.execute("SELECT * FROM peers WHERE id=?", (peer_id,)) as cursor:
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
    async with app.db_connection.execute("SELECT * FROM peer_history WHERE peer_id=? ORDER BY timestamp ASC LIMIT 50 OFFSET ?", (peer_id, page * 50)) as cursor:
        total_pages = await app.db_connection.execute("SELECT COUNT(*) FROM peer_history WHERE peer_id=?", (peer_id,))
        total_pages = await total_pages.fetchone()
        total_pages = total_pages[0] / 50
        return jsonify_peer_history(await cursor.fetchall(), total_pages)
    
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
    async with app.db_connection.execute("SELECT * FROM versions_history LIMIT 50 OFFSET ?", (page * 50,)) as cursor:
        total_pages = await app.db_connection.execute("SELECT COUNT(*) FROM versions_history")
        total_pages = await total_pages.fetchone()
        total_pages = total_pages[0] / 50
        return jsonify_versions_history(await cursor.fetchall(), total_pages)

@app.get("/nodes/online")
async def get_nodes_online():
    """Get the number of nodes online."""
    async with app.db_connection.execute("SELECT COUNT(*) FROM peers WHERE online=?", (1,)) as cursor:
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
    async with app.db_connection.execute("SELECT COUNT(*) FROM peer_history WHERE peer_id=? AND online=1 AND timestamp > ?", (peer_id, int(time.time()) - amount * period)) as cursor:
        count_online = await cursor.fetchone()
        async with app.db_connection.execute("SELECT COUNT(*) FROM peer_history WHERE peer_id=? AND timestamp > ?", (peer_id, int(time.time()) - amount * period)) as cursor:
            count_total = await cursor.fetchone()
            return {"percentage": count_online[0] / count_total[0] * 100}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
