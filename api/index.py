import requests
from flask import Flask

app = Flask(__name__)

# =============== UNITED EMPIRES ===============

# Server Stuff

@app.route("/ue/v1/server/status", methods=["GET"])
def server_status():
    request = requests.get("https://mcstatus.xdpxi.dev/api/v1/ue.xdpxi.net:59280")

    if request.status_code == 200:
        return request.json()

    return 'Server status unresponsive', 500

@app.route("/ue/v1/server/start", methods=["POST"])
def start_server():
    return 'Work in progress', 501

@app.route("/ue/v1/server/stop", methods=["POST"])
def stop_server():
    return 'Work in progress', 501

@app.route("/ue/v1/server/restart", methods=["POST"])
def restart_server():
    return 'Work in progress', 501


# Account Stuff

@app.route("/ue/v1/account/userinfo/<path:userid>", methods=["GET"])
def account_information(userid):


    return 'Work in progress', 501


# =============== XDPXI ===============

# something idk

# =====================================

if __name__ == "__main__":
    app.run(debug=True)