from flask import Flask, render_template, request, redirect, url_for, flash
import requests, time

API_URL = "http://45.134.222.45:8000"

app = Flask(__name__)

@app.template_filter('date')
def date_filter(s):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s))

def show_days(s):
    days = s // 86400
    return days

@app.template_filter('uptime')
def uptime_filter(s):
    days = show_days(s)
    return f"{days} days, {time.strftime('%H hours, %M minutes, %S seconds', time.gmtime(s))}"

@app.template_filter('reverse')
def reverse_filter(s):
    return reversed(s)

@app.template_filter('round')
def round_filter(s, n):
    return round(s, n)

@app.route("/")
def index():
    online_nodes = requests.get(f"{API_URL}/nodes/online").json()
    return render_template("index.html", online_nodes=online_nodes["count"])

def get_all_peers():
    total = []
    page = 0
    while True:
        peers = requests.get(f"{API_URL}/peers?page={page}").json()
        total.append(peers[0])
        if peers[1]["pages"] == page:
            break
        page += 1
    return total
    

@app.route("/versions")
def versions():
    peers = get_all_peers()
    versions = {}
    sub_versions = {}
    for page in peers:
        for peer in page:
            if peer["version"] not in versions:
                versions[peer["version"]] = 1
            else:
                versions[peer["version"]] += 1
            if peer["sub_version"] not in sub_versions:
                sub_versions[peer["sub_version"]] = 1
            else:
                sub_versions[peer["sub_version"]] += 1
    return render_template("versions.html", versions=versions, sub_versions=sub_versions)

@app.route("/nodes")
def nodes():
    page = request.args.get("page", 0)
    if page != 0:
        page = int(page) - 1
    peers = requests.get(f"{API_URL}/peers?page={page}").json()
    return render_template("nodes.html", nodes=peers[0], total_pages=peers[1]["pages"], current_page=page + 1)

@app.route("/nodes/<id>")
def node(id):
    peer = requests.get(f"{API_URL}/peer/get/{id}/").json()
    peer_history = requests.get(f"{API_URL}/peer/{id}/history?page=0").json()
    average_24h, average_7d, average_30d, average_365d = None, None, None, None
    average_1h = requests.get(f"{API_URL}/peer/{id}/uptime/percentage/1/hour").json()["percentage"]
    if peer["uptime"] > 3600:
        average_24h = requests.get(f"{API_URL}/peer/{id}/uptime/percentage/24/hour").json()["percentage"]
    if peer["uptime"] > 86400:
        average_7d = requests.get(f"{API_URL}/peer/{id}/uptime/percentage/7/day").json()["percentage"]
    if peer["uptime"] > 2592000:
        average_30d = requests.get(f"{API_URL}/peer/{id}/uptime/percentage/30/day").json()["percentage"]
    if peer["uptime"] > 31536000:
        average_365d = requests.get(f"{API_URL}/peer/{id}/uptime/percentage/365/day").json()["percentage"]
    return render_template("node.html", node=peer["peer"], node_uptime=peer["uptime"], history=peer_history[0], average_1h=average_1h, average_24h=average_24h, average_7d=average_7d, average_30d=average_30d, average_365d=average_365d)

@app.route("/nodes/<ip>/<port>")
def node_by_ip(ip, port):
    peer = requests.get(f"{API_URL}/peer/get/{ip}/{port}").json()
    node_id = peer["peer"]["id"]
    return redirect(url_for("node", id=node_id))

if __name__ == "__main__":
    ssl_context = ('cert.pem', 'key.pem')
    app.run(ssl_context=ssl_context, port=443, host="0.0.0.0")
